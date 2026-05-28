import io
import numpy as np
import pandas as pd
import xarray as xr
import streamlit as st
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from streamlit.components.v1 import html
from css.styleDashboard import color_fondo_dash

st.set_page_config(page_title="Mapa PP + Viento", layout="centered")

st.markdown(color_fondo_dash,unsafe_allow_html=True)

st.title("Mapas estacionales de precipitación (%) y viento")


st.markdown("""
### Metodología de cálculo

**Porcentaje mensual de precipitación**

% PP mensual = precipitación del mes / precipitación anual del año × 100

**Verano DJF**

% PP verano DJF = %Dic + %Ene + %Feb

Para un año seleccionado:

DJF año presente = diciembre del año anterior + enero del año presente + febrero del año presente

Ejemplo:

DJF 2020 = diciembre 2019 + enero 2020 + febrero 2020

**Invierno JJA**

% PP invierno JJA = %Jun + %Jul + %Ago

**Viento promedio**

u_prom = promedio de la componente zonal u  
v_prom = promedio de la componente meridional v  

Velocidad = sqrt(u_prom² + v_prom²)

Dirección = flechas usando u_prom y v_prom

El promedio del viento se calcula vectorialmente, no promediando solo velocidades.
""")


def open_nc(file):
    try:
        return xr.open_dataset(file, engine="netcdf4")
    except Exception:
        return xr.open_dataset(file, engine="h5netcdf")


def normalize_time(ds):
    if "valid_time" in ds.coords:
        ds = ds.rename({"valid_time": "time"})

    if "time" not in ds.coords:
        raise ValueError("El archivo NetCDF no tiene coordenada de tiempo válida.")

    return ds


def get_lat_lon_names(ds):
    lat_name = None
    lon_name = None

    for name in ["latitude", "lat", "y"]:
        if name in ds.coords:
            lat_name = name
            break

    for name in ["longitude", "lon", "x"]:
        if name in ds.coords:
            lon_name = name
            break

    if lat_name is None or lon_name is None:
        raise ValueError("No se encontraron coordenadas de latitud/longitud.")

    return lat_name, lon_name


def guess_pp_variable(ds):
    for var in ["tp", "precip", "precipitation", "pr"]:
        if var in ds.data_vars:
            return var

    if len(ds.data_vars) == 1:
        return list(ds.data_vars)[0]

    raise ValueError("No se pudo identificar la variable de precipitación.")


def guess_wind_variables(ds):
    u_var = None
    v_var = None

    for var in ["u", "u10", "uwnd", "uas"]:
        if var in ds.data_vars:
            u_var = var
            break

    for var in ["v", "v10", "vwnd", "vas"]:
        if var in ds.data_vars:
            v_var = var
            break

    if u_var is None or v_var is None:
        raise ValueError("No se pudieron identificar las variables de viento u y v.")

    return u_var, v_var


def reduce_extra_dims(da):
    valid_dims = ["time", "latitude", "longitude", "lat", "lon", "y", "x"]

    for dim in list(da.dims):
        if dim not in valid_dims:
            da = da.isel({dim: 0})

    return da


def check_compatibility(ds_pp, ds_wind):
    pp_lat, pp_lon = get_lat_lon_names(ds_pp)
    wind_lat, wind_lon = get_lat_lon_names(ds_wind)

    if not np.allclose(ds_pp[pp_lat].values, ds_wind[wind_lat].values):
        raise ValueError("Las latitudes no coinciden entre precipitación y viento.")

    if not np.allclose(ds_pp[pp_lon].values, ds_wind[wind_lon].values):
        raise ValueError("Las longitudes no coinciden entre precipitación y viento.")

    pp_months = pd.to_datetime(ds_pp.time.values).to_period("M")
    wind_months = pd.to_datetime(ds_wind.time.values).to_period("M")

    common_months = sorted(set(pp_months).intersection(set(wind_months)))

    if not common_months:
        raise ValueError("No hay meses comunes entre precipitación y viento.")

    return common_months


def seasonal_months(period, year):
    if period == "Verano DJF":
        return [
            pd.Period(f"{year - 1}-12", freq="M"),
            pd.Period(f"{year}-01", freq="M"),
            pd.Period(f"{year}-02", freq="M"),
        ]

    if period == "Invierno JJA":
        return [
            pd.Period(f"{year}-06", freq="M"),
            pd.Period(f"{year}-07", freq="M"),
            pd.Period(f"{year}-08", freq="M"),
        ]

    raise ValueError("Periodo no reconocido.")


def get_available_years(common_months, period):
    years = sorted(set(m.year for m in common_months))
    valid_years = []

    for year in years:
        months = seasonal_months(period, year)
        if all(m in common_months for m in months):
            valid_years.append(year)

    return valid_years


def select_month(ds, month_period):
    time_periods = pd.to_datetime(ds.time.values).to_period("M")
    idx = np.where(time_periods == month_period)[0]

    if len(idx) != 1:
        raise ValueError(f"No se encontró exactamente un registro para {month_period}.")

    return ds.isel(time=idx[0])


def select_season(ds, months):
    time_periods = pd.to_datetime(ds.time.values).to_period("M")
    mask = np.isin(time_periods, months)

    if mask.sum() != 3:
        raise ValueError("No están completos los 3 meses del periodo seleccionado.")

    return ds.isel(time=mask)


def calculate_precip_percentage_one_year(ds_pp, pp_var, period, year):
    tp = reduce_extra_dims(ds_pp[pp_var])
    months = seasonal_months(period, year)

    seasonal_percent_parts = []

    for month in months:
        monthly_pp = select_month(ds_pp[[pp_var]], month)[pp_var]
        monthly_pp = reduce_extra_dims(monthly_pp)

        annual_pp = tp.sel(time=str(month.year)).sum(dim="time")

        monthly_percent = monthly_pp / annual_pp * 100
        seasonal_percent_parts.append(monthly_percent)

    return sum(seasonal_percent_parts)


def calculate_wind_average_one_year(ds_wind, u_var, v_var, period, year):
    months = seasonal_months(period, year)
    ds_season = select_season(ds_wind[[u_var, v_var]], months)

    u = reduce_extra_dims(ds_season[u_var]).mean(dim="time")
    v = reduce_extra_dims(ds_season[v_var]).mean(dim="time")

    speed = np.sqrt(u**2 + v**2)

    return u, v, speed


def calculate_precip_percentage_mean_all_years(ds_pp, pp_var, period, years):
    maps = []

    for year in years:
        result = calculate_precip_percentage_one_year(ds_pp, pp_var, period, year)
        maps.append(result)

    return xr.concat(maps, dim="year").assign_coords(year=years).mean(dim="year")


def calculate_wind_average_mean_all_years(ds_wind, u_var, v_var, period, years):
    u_maps = []
    v_maps = []

    for year in years:
        u, v, _ = calculate_wind_average_one_year(ds_wind, u_var, v_var, period, year)
        u_maps.append(u)
        v_maps.append(v)

    u_mean = xr.concat(u_maps, dim="year").assign_coords(year=years).mean(dim="year")
    v_mean = xr.concat(v_maps, dim="year").assign_coords(year=years).mean(dim="year")

    speed_mean = np.sqrt(u_mean**2 + v_mean**2)

    return u_mean, v_mean, speed_mean


def get_lon_lat_from_dataarray(da):
    lat_name, lon_name = get_lat_lon_names(da.to_dataset(name="tmp"))
    return da[lon_name].values, da[lat_name].values


def plot_map(pp_percent, u, v, speed, title):
    lon, lat = get_lon_lat_from_dataarray(pp_percent)

    fig = plt.figure(figsize=(10, 10))
    ax = plt.axes(projection=ccrs.PlateCarree())

    ax.set_extent([-90, -30, -60, 20], crs=ccrs.PlateCarree())

    pp_values = pp_percent.values

    vmin = float(np.nanpercentile(pp_values, 5))
    vmax = float(np.nanpercentile(pp_values, 95))

    if np.isclose(vmin, vmax):
        vmin = float(np.nanmin(pp_values))
        vmax = float(np.nanmax(pp_values))

    levels = np.linspace(vmin, vmax, 14)

    cf = ax.contourf(
        lon,
        lat,
        pp_values,
        levels=levels,
        cmap="Spectral_r",
        transform=ccrs.PlateCarree(),
        extend="both",
    )

    step = max(1, int(len(lon) / 35))

    q = ax.quiver(
        lon[::step],
        lat[::step],
        u.values[::step, ::step],
        v.values[::step, ::step],
        speed.values[::step, ::step],
        transform=ccrs.PlateCarree(),
        scale=250,
        width=0.0022,
        headwidth=3,
        headlength=4,
    )

    ax.quiverkey(
        q,
        X=0.86,
        Y=-0.08,
        U=10,
        label="10 m/s",
        labelpos="E",
        coordinates="axes",
    )

    ax.coastlines(linewidth=0.8)
    ax.add_feature(cfeature.BORDERS, linewidth=0.6)
    ax.add_feature(cfeature.LAND, facecolor="none", edgecolor="black", linewidth=0.3)

    gl = ax.gridlines(draw_labels=True, linewidth=0.3, alpha=0.5)
    gl.top_labels = False
    gl.right_labels = False

    cbar = plt.colorbar(cf, ax=ax, orientation="horizontal", pad=0.08, shrink=0.75)
    cbar.set_label("% de precipitación anual")

    ax.set_title(title, fontsize=14, weight="bold")

    return fig


pp_file = st.file_uploader("Sube archivo NetCDF de precipitación", type=["nc"])
wind_file = st.file_uploader("Sube archivo NetCDF de viento", type=["nc"])

if pp_file and wind_file:
    try:
        ds_pp = normalize_time(open_nc(pp_file))
        ds_wind = normalize_time(open_nc(wind_file))

        pp_var = guess_pp_variable(ds_pp)
        u_var, v_var = guess_wind_variables(ds_wind)

        common_months = check_compatibility(ds_pp, ds_wind)

        st.success("Archivos NetCDF cargados y validados correctamente.")

        st.write(f"Variable de precipitación detectada: `{pp_var}`")
        st.write(f"Variables de viento detectadas: `{u_var}` y `{v_var}`")

        col1, col2, col3 = st.columns(3)

        with col1:
            period = st.selectbox("Periodo", ["Verano DJF", "Invierno JJA"])

        valid_years = get_available_years(common_months, period)

        if not valid_years:
            st.error("No hay años completos disponibles para el periodo seleccionado.")
            st.stop()

        with col2:
            mode = st.selectbox(
                "Tipo de mapa",
                ["Mapa por año", "Mapa promedio de todos los años"],
            )

        with col3:
            if mode == "Mapa por año":
                selected_year = st.selectbox(
                    "Año",
                    valid_years,
                    index=len(valid_years) - 1,
                )
            else:
                selected_year = None
                st.write("Se usará todo el periodo disponible.")

        if st.button("Generar mapa"):
            if mode == "Mapa por año":
                pp_percent = calculate_precip_percentage_one_year(
                    ds_pp=ds_pp,
                    pp_var=pp_var,
                    period=period,
                    year=selected_year,
                )

                u, v, speed = calculate_wind_average_one_year(
                    ds_wind=ds_wind,
                    u_var=u_var,
                    v_var=v_var,
                    period=period,
                    year=selected_year,
                )

                title = (
                    f"{period} {selected_year}\n"
                    f"% precipitación anual + viento promedio"
                )

                file_name = f"mapa_{period.replace(' ', '_')}_{selected_year}.png"

            else:
                pp_percent = calculate_precip_percentage_mean_all_years(
                    ds_pp=ds_pp,
                    pp_var=pp_var,
                    period=period,
                    years=valid_years,
                )

                u, v, speed = calculate_wind_average_mean_all_years(
                    ds_wind=ds_wind,
                    u_var=u_var,
                    v_var=v_var,
                    period=period,
                    years=valid_years,
                )

                title = (
                    f"{period}\n"
                    f"Promedio {min(valid_years)}-{max(valid_years)}\n"
                    f"% precipitación anual + viento promedio"
                )

                file_name = (
                    f"mapa_promedio_{period.replace(' ', '_')}_"
                    f"{min(valid_years)}_{max(valid_years)}.png"
                )

            fig = plot_map(pp_percent, u, v, speed, title)

            st.pyplot(fig)

            buffer = io.BytesIO()
            fig.savefig(buffer, format="png", dpi=300, bbox_inches="tight")
            buffer.seek(0)

            st.download_button(
                label="Descargar mapa PNG",
                data=buffer,
                file_name=file_name,
                mime="image/png",
            )

    except Exception as e:
        st.error(f"Error: {e}")

else:
    st.info("Sube ambos archivos NetCDF para iniciar el procesamiento.")



html("""
<script>
window.top.document.querySelectorAll(`[href*="streamlit.io"]`).forEach(e => e.setAttribute("style", "display: none;"));
</script>
     """)
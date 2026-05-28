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

st.title("Mapas estacionales de precipitación acumulada y viento")


st.markdown("""
### Metodología de cálculo

La precipitación del archivo NetCDF se convierte a milímetros antes de realizar los cálculos.

Si la variable de precipitación viene en metros:

1 m = 1000 mm

**Precipitación acumulada estacional**

PP mensual = precipitación mensual en milímetros

PP verano DJF = PP Dic + PP Ene + PP Feb

PP invierno JJA = PP Jun + PP Jul + PP Ago

Para verano DJF:

DJF año presente = diciembre del año anterior + enero del año presente + febrero del año presente

Ejemplo:

DJF 2020 = diciembre 2019 + enero 2020 + febrero 2020

**Viento promedio**

u_prom = promedio de la componente zonal u

v_prom = promedio de la componente meridional v

Velocidad = sqrt(u_prom² + v_prom²)

Dirección = flechas usando u_prom y v_prom

El promedio del viento se calcula vectorialmente, no promediando solo velocidades.
""")


COUNTRY_EXTENTS = {
    "Toda Sudamérica": [-90, -30, -60, 20],
    "Perú": [-82, -68, -19, 1],
    "Brasil": [-75, -34, -35, 7],
    "Bolivia": [-70, -57, -24, -8],
    "Chile": [-76, -66, -56, -17],
    "Argentina": [-74, -52, -56, -20],
    "Ecuador": [-82, -75, -6, 2],
    "Colombia": [-80, -66, -5, 14],
    "Venezuela": [-74, -59, 0, 13],
    "Paraguay": [-63, -54, -28, -19],
    "Uruguay": [-59, -52, -36, -30],
}


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


def ensure_lat_lon_order(da):
    lat_name, lon_name = get_lat_lon_names(da.to_dataset(name="tmp"))
    return da.transpose(lat_name, lon_name)


def convert_pp_to_mm(da):
    units = str(da.attrs.get("units", "")).lower().strip()

    if units in ["m", "meter", "meters", "metre", "metres"]:
        da = da * 1000.0
        da.attrs["units"] = "mm"
        return da

    if units in ["mm", "millimeter", "millimeters", "millimetre", "millimetres"]:
        da.attrs["units"] = "mm"
        return da

    st.warning(
        "No se pudo identificar claramente la unidad de precipitación. "
        "Se asumirá que la precipitación ya está en milímetros."
    )
    da.attrs["units"] = "mm"
    return da


def prepare_pp_dataset(ds_pp, pp_var):
    ds_pp = ds_pp.copy()
    pp_mm = convert_pp_to_mm(ds_pp[pp_var])
    pp_mm.name = pp_var
    ds_pp[pp_var] = pp_mm
    ds_pp[pp_var].attrs["units"] = "mm"
    return ds_pp


def check_compatibility(ds_pp, ds_wind):
    pp_lat, pp_lon = get_lat_lon_names(ds_pp)
    wind_lat, wind_lon = get_lat_lon_names(ds_wind)

    if not np.allclose(ds_pp[pp_lat].values, ds_wind[wind_lat].values):
        raise ValueError("Las latitudes no coinciden entre precipitación y viento.")

    if not np.allclose(ds_pp[pp_lon].values, ds_wind[wind_lon].values):
        raise ValueError("Las longitudes no coinciden entre precipitación y viento.")

    pp_months = sorted(set(pd.to_datetime(ds_pp.time.values).to_period("M")))
    wind_months = sorted(set(pd.to_datetime(ds_wind.time.values).to_period("M")))

    common_months = sorted(set(pp_months).intersection(set(wind_months)))

    if not common_months:
        raise ValueError("No hay meses comunes entre precipitación y viento.")

    return pp_months, wind_months, common_months


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


def get_available_years(pp_months, wind_months, period):
    years = sorted(set(m.year for m in pp_months).intersection(set(m.year for m in wind_months)))
    valid_years = []

    for year in years:
        months = seasonal_months(period, year)

        pp_has_months = all(m in pp_months for m in months)
        wind_has_months = all(m in wind_months for m in months)

        if pp_has_months and wind_has_months:
            valid_years.append(year)

    return valid_years


def select_season(ds, months):
    time_periods = pd.to_datetime(ds.time.values).to_period("M")
    mask = np.isin(time_periods, months)

    if mask.sum() != 3:
        raise ValueError("No están completos los 3 meses del periodo seleccionado.")

    return ds.isel(time=mask)


def calculate_precip_accumulated_one_year(ds_pp, pp_var, period, year):
    months = seasonal_months(period, year)
    ds_season = select_season(ds_pp[[pp_var]], months)

    pp_accumulated_mm = reduce_extra_dims(ds_season[pp_var]).sum(dim="time")
    pp_accumulated_mm = ensure_lat_lon_order(pp_accumulated_mm)
    pp_accumulated_mm.attrs["units"] = "mm"

    return pp_accumulated_mm


def calculate_precip_accumulated_mean_years(ds_pp, pp_var, period, years):
    maps = []

    for year in years:
        result = calculate_precip_accumulated_one_year(
            ds_pp=ds_pp,
            pp_var=pp_var,
            period=period,
            year=year,
        )
        maps.append(result)

    result_mean = xr.concat(maps, dim="year").assign_coords(year=years).mean(dim="year")
    result_mean.attrs["units"] = "mm"

    return result_mean


def calculate_wind_average_one_year(ds_wind, u_var, v_var, period, year):
    months = seasonal_months(period, year)
    ds_season = select_season(ds_wind[[u_var, v_var]], months)

    u = reduce_extra_dims(ds_season[u_var]).mean(dim="time")
    v = reduce_extra_dims(ds_season[v_var]).mean(dim="time")

    u = ensure_lat_lon_order(u)
    v = ensure_lat_lon_order(v)

    speed = np.sqrt(u**2 + v**2)

    return u, v, speed


def calculate_wind_average_mean_years(ds_wind, u_var, v_var, period, years):
    u_maps = []
    v_maps = []

    for year in years:
        u, v, _ = calculate_wind_average_one_year(
            ds_wind=ds_wind,
            u_var=u_var,
            v_var=v_var,
            period=period,
            year=year,
        )
        u_maps.append(u)
        v_maps.append(v)

    u_mean = xr.concat(u_maps, dim="year").assign_coords(year=years).mean(dim="year")
    v_mean = xr.concat(v_maps, dim="year").assign_coords(year=years).mean(dim="year")

    speed_mean = np.sqrt(u_mean**2 + v_mean**2)

    return u_mean, v_mean, speed_mean


def get_lon_lat_from_dataarray(da):
    lat_name, lon_name = get_lat_lon_names(da.to_dataset(name="tmp"))
    return da[lon_name].values, da[lat_name].values


def get_quiver_style(map_extent, lon):
    lon_span = abs(map_extent[1] - map_extent[0])
    lat_span = abs(map_extent[3] - map_extent[2])
    map_span = max(lon_span, lat_span)

    if map_span >= 50:
        step = max(1, int(len(lon) / 35))
        quiver_scale = 250
        quiver_width = 0.0022
        quiver_key = 10

    elif map_span >= 25:
        step = max(1, int(len(lon) / 28))
        quiver_scale = 150
        quiver_width = 0.0028
        quiver_key = 10

    elif map_span >= 12:
        step = max(1, int(len(lon) / 22))
        quiver_scale = 75
        quiver_width = 0.0038
        quiver_key = 10

    else:
        step = max(1, int(len(lon) / 16))
        quiver_scale = 45
        quiver_width = 0.0045
        quiver_key = 5

    return step, quiver_scale, quiver_width, quiver_key


def plot_map(pp_data, u, v, speed, title, map_extent):
    lon, lat = get_lon_lat_from_dataarray(pp_data)

    fig = plt.figure(figsize=(11, 10))
    ax = plt.axes(projection=ccrs.PlateCarree())

    ax.set_extent(map_extent, crs=ccrs.PlateCarree())

    pp_values = pp_data.values

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
        cmap="Blues",
        transform=ccrs.PlateCarree(),
        extend="both",
    )

    step, quiver_scale, quiver_width, quiver_key = get_quiver_style(
        map_extent=map_extent,
        lon=lon,
    )

    q = ax.quiver(
        lon[::step],
        lat[::step],
        u.values[::step, ::step],
        v.values[::step, ::step],
        speed.values[::step, ::step],
        cmap="plasma",
        transform=ccrs.PlateCarree(),
        scale=quiver_scale,
        width=quiver_width,
        headwidth=3.5,
        headlength=4.5,
        edgecolor="black",
        linewidth=0.15,
    )

    ax.quiverkey(
        q,
        X=0.83,
        Y=-0.08,
        U=quiver_key,
        label=f"{quiver_key} m/s",
        labelpos="E",
        coordinates="axes",
    )

    ax.coastlines(linewidth=0.8)
    ax.add_feature(cfeature.BORDERS, linewidth=0.6)
    ax.add_feature(cfeature.LAND, facecolor="none", edgecolor="black", linewidth=0.3)

    gl = ax.gridlines(draw_labels=True, linewidth=0.3, alpha=0.5)
    gl.top_labels = False
    gl.right_labels = False

    cbar_pp = plt.colorbar(
        cf,
        ax=ax,
        orientation="horizontal",
        pad=0.08,
        shrink=0.75,
    )
    cbar_pp.set_label("Precipitación acumulada estacional (mm)")

    cbar_wind = plt.colorbar(
        q,
        ax=ax,
        orientation="vertical",
        pad=0.03,
        shrink=0.65,
    )
    cbar_wind.set_label("Velocidad del viento (m/s)")

    ax.set_title(title, fontsize=14, weight="bold")

    return fig


pp_file = st.file_uploader("Sube archivo NetCDF de precipitación", type=["nc"])
wind_file = st.file_uploader("Sube archivo NetCDF de viento", type=["nc"])

if pp_file and wind_file:
    try:
        ds_pp = normalize_time(open_nc(pp_file))
        ds_wind = normalize_time(open_nc(wind_file))

        pp_var = guess_pp_variable(ds_pp)
        ds_pp = prepare_pp_dataset(ds_pp, pp_var)

        u_var, v_var = guess_wind_variables(ds_wind)

        pp_months, wind_months, common_months = check_compatibility(ds_pp, ds_wind)

        st.success("Archivos NetCDF cargados y validados correctamente.")
        st.write(f"Variable de precipitación detectada: `{pp_var}`")
        st.write("Unidad de precipitación usada para los cálculos: `mm`")
        st.write(f"Variables de viento detectadas: `{u_var}` y `{v_var}`")

        col1, col2, col3 = st.columns(3)

        with col1:
            period = st.selectbox(
                "Periodo",
                ["Verano DJF", "Invierno JJA"],
            )

        with col2:
            mode = st.selectbox(
                "Tipo de mapa",
                ["Mapa por año", "Mapa promedio de años"],
            )

        with col3:
            selected_region = st.selectbox(
                "Región",
                list(COUNTRY_EXTENTS.keys()),
            )

        valid_years = get_available_years(
            pp_months=pp_months,
            wind_months=wind_months,
            period=period,
        )

        if not valid_years:
            st.error("No hay años completos para el periodo seleccionado.")
            st.stop()

        selected_year = None
        selected_years_range = None

        if mode == "Mapa por año":
            selected_year = st.selectbox(
                "Año",
                valid_years,
                index=len(valid_years) - 1,
            )

        else:
            selected_years_range = st.slider(
                "Periodo de años para calcular el promedio",
                min_value=min(valid_years),
                max_value=max(valid_years),
                value=(min(valid_years), max(valid_years)),
                step=1,
            )

        if st.button("Generar mapa"):
            map_extent = COUNTRY_EXTENTS[selected_region]

            if mode == "Mapa por año":
                pp_data = calculate_precip_accumulated_one_year(
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
                    f"{selected_region} - {period} {selected_year}\n"
                    f"Precipitación acumulada estacional + viento promedio"
                )

                file_name = (
                    f"mapa_{selected_region.replace(' ', '_')}_"
                    f"pp_acumulada_{period.replace(' ', '_')}_{selected_year}.png"
                )

            else:
                start_year, end_year = selected_years_range

                years_for_mean = [
                    year for year in valid_years
                    if start_year <= year <= end_year
                ]

                if not years_for_mean:
                    st.error("No hay años válidos dentro del periodo seleccionado.")
                    st.stop()

                pp_data = calculate_precip_accumulated_mean_years(
                    ds_pp=ds_pp,
                    pp_var=pp_var,
                    period=period,
                    years=years_for_mean,
                )

                u, v, speed = calculate_wind_average_mean_years(
                    ds_wind=ds_wind,
                    u_var=u_var,
                    v_var=v_var,
                    period=period,
                    years=years_for_mean,
                )

                title = (
                    f"{selected_region} - {period}\n"
                    f"Promedio {min(years_for_mean)}-{max(years_for_mean)}\n"
                    f"Precipitación acumulada estacional + viento promedio"
                )

                file_name = (
                    f"mapa_promedio_{selected_region.replace(' ', '_')}_"
                    f"pp_acumulada_{period.replace(' ', '_')}_"
                    f"{min(years_for_mean)}_{max(years_for_mean)}.png"
                )

            fig = plot_map(
                pp_data=pp_data,
                u=u,
                v=v,
                speed=speed,
                title=title,
                map_extent=map_extent,
            )

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
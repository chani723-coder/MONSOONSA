import io
import numpy as np
import pandas as pd
import xarray as xr
import streamlit as st
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature

from matplotlib.colors import Normalize, PowerNorm
from streamlit.components.v1 import html
from css.styleDashboard import color_fondo_dash


# ============================================================
# CONFIGURACIÓN STREAMLIT
# ============================================================

st.set_page_config(
    page_title="Mapa PP + Viento",
    layout="centered"
)

st.markdown(
    color_fondo_dash,
    unsafe_allow_html=True
)

st.title(
    "Mapas estacionales de precipitación acumulada y viento"
)


# ============================================================
# METODOLOGÍA
# ============================================================

st.markdown("""
### Metodología de cálculo

La variable de precipitación del archivo NetCDF representa el
**acumulado mensual de precipitación**.

Si la variable de precipitación viene expresada en metros:

**1 m = 1000 mm**

Por tanto, primero se realiza la conversión de metros a milímetros.

---

### Precipitación acumulada estacional

No se multiplica la precipitación por el número de días del mes.

Cada paso temporal mensual representa directamente el acumulado
correspondiente a ese mes.

#### Verano DJF

El acumulado de verano se calcula como:

**PP verano DJF = PP Dic + PP Ene + PP Feb**

Para un año determinado:

**DJF año presente = diciembre del año anterior
+ enero del año presente
+ febrero del año presente**

Por ejemplo:

**DJF 2020 = diciembre 2019 + enero 2020 + febrero 2020**

---

#### Invierno JJA

El acumulado de invierno se calcula como:

**PP invierno JJA = PP Jun + PP Jul + PP Ago**

En este caso los tres meses pertenecen al mismo año.

Por ejemplo:

**JJA 2020 = junio 2020 + julio 2020 + agosto 2020**

---

### Mapa promedio de varios años

Para cada año se calcula primero el acumulado estacional correspondiente.

Por ejemplo, para DJF:

**DJF año = Dic año anterior + Ene año + Feb año**

Después se calcula el promedio de los mapas estacionales obtenidos
para todos los años seleccionados.

---

### Viento promedio

Se calcula primero el promedio temporal de las componentes:

**u_prom = promedio de la componente zonal u**

**v_prom = promedio de la componente meridional v**

La velocidad del viento resultante se calcula como:

**Velocidad = √(u_prom² + v_prom²)**

La dirección del viento se representa mediante flechas utilizando
directamente `u_prom` y `v_prom`.

Por tanto, el viento se promedia vectorialmente y no mediante el
promedio directo de las velocidades.
""")


# ============================================================
# EXTENSIONES GEOGRÁFICAS
# ============================================================

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


# ============================================================
# PALETAS DE COLORES
# ============================================================

AVAILABLE_CMAPS = [

    "viridis",
    "plasma",
    "inferno",
    "magma",
    "cividis",
    "turbo",

    "Spectral",
    "coolwarm",
    "RdYlBu",

    "terrain",
    "gist_earth",
    "ocean",

    "YlGnBu",
    "Blues",
    "Greens",
    "Oranges",
    "Reds",
]


# ============================================================
# APERTURA NETCDF
# ============================================================

def open_nc(file):

    try:

        return xr.open_dataset(
            file,
            engine="netcdf4"
        )

    except Exception:

        return xr.open_dataset(
            file,
            engine="h5netcdf"
        )


# ============================================================
# NORMALIZAR COORDENADA TEMPORAL
# ============================================================

def normalize_time(ds):

    if "valid_time" in ds.coords:

        ds = ds.rename(
            {"valid_time": "time"}
        )

    if "time" not in ds.coords:

        raise ValueError(
            "El archivo NetCDF no tiene una coordenada "
            "de tiempo válida."
        )

    return ds


# ============================================================
# IDENTIFICAR LATITUD / LONGITUD
# ============================================================

def get_lat_lon_names(ds):

    lat_name = None
    lon_name = None

    for name in [
        "latitude",
        "lat",
        "y",
    ]:

        if name in ds.coords:

            lat_name = name
            break

    for name in [
        "longitude",
        "lon",
        "x",
    ]:

        if name in ds.coords:

            lon_name = name
            break

    if lat_name is None or lon_name is None:

        raise ValueError(
            "No se encontraron coordenadas "
            "de latitud/longitud."
        )

    return lat_name, lon_name


# ============================================================
# IDENTIFICAR VARIABLE PRECIPITACIÓN
# ============================================================

def guess_pp_variable(ds):

    for var in [
        "tp",
        "precip",
        "precipitation",
        "pr",
    ]:

        if var in ds.data_vars:

            return var

    if len(ds.data_vars) == 1:

        return list(ds.data_vars)[0]

    raise ValueError(
        "No se pudo identificar automáticamente "
        "la variable de precipitación."
    )


# ============================================================
# IDENTIFICAR VARIABLES VIENTO
# ============================================================

def guess_wind_variables(ds):

    u_var = None
    v_var = None

    for var in [
        "u",
        "u10",
        "uwnd",
        "uas",
    ]:

        if var in ds.data_vars:

            u_var = var
            break

    for var in [
        "v",
        "v10",
        "vwnd",
        "vas",
    ]:

        if var in ds.data_vars:

            v_var = var
            break

    if u_var is None or v_var is None:

        raise ValueError(
            "No se pudieron identificar automáticamente "
            "las componentes u y v del viento."
        )

    return u_var, v_var


# ============================================================
# REDUCIR DIMENSIONES ADICIONALES
# ============================================================

def reduce_extra_dims(da):

    valid_dims = [
        "time",
        "latitude",
        "longitude",
        "lat",
        "lon",
        "y",
        "x",
    ]

    for dim in list(da.dims):

        if dim not in valid_dims:

            da = da.isel(
                {dim: 0}
            )

    return da


# ============================================================
# ORDEN LAT / LON
# ============================================================

def ensure_lat_lon_order(da):

    lat_name, lon_name = get_lat_lon_names(
        da.to_dataset(name="tmp")
    )

    return da.transpose(
        lat_name,
        lon_name
    )


# ============================================================
# CONVERSIÓN PRECIPITACIÓN A MM
# ============================================================

def convert_pp_to_mm(da):

    units = str(
        da.attrs.get("units", "")
    ).lower().strip()

    # --------------------------------------------------------
    # Metros -> milímetros
    # --------------------------------------------------------

    if units in [
        "m",
        "meter",
        "meters",
        "metre",
        "metres",
    ]:

        da = da * 1000.0

        da.attrs["units"] = "mm"

        return da

    # --------------------------------------------------------
    # Si ya está en mm
    # --------------------------------------------------------

    if "mm" in units:

        da.attrs["units"] = "mm"

        return da

    raise ValueError(
        f"No se reconoce la unidad de precipitación: '{units}'. "
        "No se realizará una conversión automática."
    )


# ============================================================
# PREPARAR DATASET PRECIPITACIÓN
# ============================================================

def prepare_pp_dataset(
    ds_pp,
    pp_var
):

    ds_pp = ds_pp.copy()

    pp_mm = convert_pp_to_mm(
        ds_pp[pp_var]
    )

    pp_mm.name = pp_var

    ds_pp[pp_var] = pp_mm

    ds_pp[pp_var].attrs["units"] = "mm"

    return ds_pp


# ============================================================
# COMPATIBILIDAD PP / VIENTO
# ============================================================

def check_compatibility(
    ds_pp,
    ds_wind
):

    pp_lat, pp_lon = get_lat_lon_names(
        ds_pp
    )

    wind_lat, wind_lon = get_lat_lon_names(
        ds_wind
    )

    # --------------------------------------------------------
    # Dimensiones espaciales
    # --------------------------------------------------------

    if (
        ds_pp[pp_lat].size
        != ds_wind[wind_lat].size
    ):

        raise ValueError(
            "La cantidad de latitudes no coincide "
            "entre precipitación y viento."
        )

    if (
        ds_pp[pp_lon].size
        != ds_wind[wind_lon].size
    ):

        raise ValueError(
            "La cantidad de longitudes no coincide "
            "entre precipitación y viento."
        )

    # --------------------------------------------------------
    # Coordenadas espaciales
    # --------------------------------------------------------

    if not np.allclose(
        ds_pp[pp_lat].values,
        ds_wind[wind_lat].values,
    ):

        raise ValueError(
            "Las latitudes no coinciden "
            "entre precipitación y viento."
        )

    if not np.allclose(
        ds_pp[pp_lon].values,
        ds_wind[wind_lon].values,
    ):

        raise ValueError(
            "Las longitudes no coinciden "
            "entre precipitación y viento."
        )

    # --------------------------------------------------------
    # Meses disponibles
    # --------------------------------------------------------

    pp_months = sorted(
        set(
            pd.to_datetime(
                ds_pp.time.values
            ).to_period("M")
        )
    )

    wind_months = sorted(
        set(
            pd.to_datetime(
                ds_wind.time.values
            ).to_period("M")
        )
    )

    common_months = sorted(
        set(pp_months).intersection(
            set(wind_months)
        )
    )

    if not common_months:

        raise ValueError(
            "No existen meses comunes entre "
            "precipitación y viento."
        )

    return (
        pp_months,
        wind_months,
        common_months,
    )


# ============================================================
# MESES DE CADA ESTACIÓN
# ============================================================

def seasonal_months(
    period,
    year
):

    if period == "Verano DJF":

        return [

            pd.Period(
                f"{year - 1}-12",
                freq="M"
            ),

            pd.Period(
                f"{year}-01",
                freq="M"
            ),

            pd.Period(
                f"{year}-02",
                freq="M"
            ),
        ]

    if period == "Invierno JJA":

        return [

            pd.Period(
                f"{year}-06",
                freq="M"
            ),

            pd.Period(
                f"{year}-07",
                freq="M"
            ),

            pd.Period(
                f"{year}-08",
                freq="M"
            ),
        ]

    raise ValueError(
        "Periodo estacional no reconocido."
    )


# ============================================================
# AÑOS DISPONIBLES
# ============================================================

def get_available_years(
    pp_months,
    wind_months,
    period
):

    years = sorted(
        set(
            m.year
            for m in pp_months
        ).intersection(
            set(
                m.year
                for m in wind_months
            )
        )
    )

    valid_years = []

    for year in years:

        months = seasonal_months(
            period,
            year
        )

        pp_complete = all(
            month in pp_months
            for month in months
        )

        wind_complete = all(
            month in wind_months
            for month in months
        )

        if (
            pp_complete
            and wind_complete
        ):

            valid_years.append(
                year
            )

    return valid_years


# ============================================================
# SELECCIONAR LOS 3 MESES
# ============================================================

def select_season(
    ds,
    months
):

    time_periods = pd.to_datetime(
        ds.time.values
    ).to_period("M")

    mask = np.isin(
        time_periods,
        months
    )

    if mask.sum() != 3:

        raise ValueError(
            "No están completos exactamente los "
            "3 meses del periodo seleccionado."
        )

    return ds.isel(
        time=mask
    )


# ============================================================
# PP ACUMULADA PARA UN AÑO
# ============================================================

def calculate_precip_accumulated_one_year(
    ds_pp,
    pp_var,
    period,
    year
):

    months = seasonal_months(
        period,
        year
    )

    ds_season = select_season(
        ds_pp[[pp_var]],
        months
    )

    # --------------------------------------------------------
    # Cada timestep representa directamente el
    # ACUMULADO MENSUAL de precipitación.
    #
    # NO se multiplica por el número de días.
    #
    # DJF = Dic + Ene + Feb
    # JJA = Jun + Jul + Ago
    # --------------------------------------------------------

    pp_monthly_mm = reduce_extra_dims(
        ds_season[pp_var]
    )

    pp_accumulated_mm = (
        pp_monthly_mm
        .sum(
            dim="time",
            skipna=True
        )
    )

    pp_accumulated_mm = (
        ensure_lat_lon_order(
            pp_accumulated_mm
        )
    )

    pp_accumulated_mm.attrs[
        "units"
    ] = "mm"

    return pp_accumulated_mm


# ============================================================
# PROMEDIO DE ACUMULADOS ESTACIONALES
# ============================================================

def calculate_precip_accumulated_mean_years(
    ds_pp,
    pp_var,
    period,
    years
):

    maps = []

    for year in years:

        result = (
            calculate_precip_accumulated_one_year(
                ds_pp=ds_pp,
                pp_var=pp_var,
                period=period,
                year=year,
            )
        )

        maps.append(
            result
        )

    result_mean = (
        xr.concat(
            maps,
            dim="year"
        )
        .assign_coords(
            year=years
        )
        .mean(
            dim="year",
            skipna=True
        )
    )

    result_mean.attrs[
        "units"
    ] = "mm"

    return result_mean


# ============================================================
# VIENTO PARA UN AÑO
# ============================================================

def calculate_wind_average_one_year(
    ds_wind,
    u_var,
    v_var,
    period,
    year
):

    months = seasonal_months(
        period,
        year
    )

    ds_season = select_season(
        ds_wind[
            [
                u_var,
                v_var,
            ]
        ],
        months
    )

    # --------------------------------------------------------
    # Promedio vectorial
    # --------------------------------------------------------

    u = reduce_extra_dims(
        ds_season[u_var]
    ).mean(
        dim="time",
        skipna=True
    )

    v = reduce_extra_dims(
        ds_season[v_var]
    ).mean(
        dim="time",
        skipna=True
    )

    u = ensure_lat_lon_order(u)
    v = ensure_lat_lon_order(v)

    speed = np.sqrt(
        u ** 2
        +
        v ** 2
    )

    return (
        u,
        v,
        speed,
    )


# ============================================================
# VIENTO PROMEDIO DE VARIOS AÑOS
# ============================================================

def calculate_wind_average_mean_years(
    ds_wind,
    u_var,
    v_var,
    period,
    years
):

    u_maps = []
    v_maps = []

    for year in years:

        u, v, _ = (
            calculate_wind_average_one_year(
                ds_wind=ds_wind,
                u_var=u_var,
                v_var=v_var,
                period=period,
                year=year,
            )
        )

        u_maps.append(u)
        v_maps.append(v)

    u_mean = (
        xr.concat(
            u_maps,
            dim="year"
        )
        .assign_coords(
            year=years
        )
        .mean(
            dim="year",
            skipna=True
        )
    )

    v_mean = (
        xr.concat(
            v_maps,
            dim="year"
        )
        .assign_coords(
            year=years
        )
        .mean(
            dim="year",
            skipna=True
        )
    )

    speed_mean = np.sqrt(
        u_mean ** 2
        +
        v_mean ** 2
    )

    return (
        u_mean,
        v_mean,
        speed_mean,
    )


# ============================================================
# OBTENER LONGITUD / LATITUD
# ============================================================

def get_lon_lat_from_dataarray(
    da
):

    lat_name, lon_name = (
        get_lat_lon_names(
            da.to_dataset(
                name="tmp"
            )
        )
    )

    return (
        da[lon_name].values,
        da[lat_name].values,
    )


# ============================================================
# RECORTAR DATAARRAY A LA REGIÓN VISIBLE
# ============================================================

def crop_dataarray_to_extent(
    da,
    map_extent
):

    lon_min, lon_max, lat_min, lat_max = (
        map_extent
    )

    lat_name, lon_name = (
        get_lat_lon_names(
            da.to_dataset(
                name="tmp"
            )
        )
    )

    lon_values = (
        da[lon_name].values
    )

    lat_values = (
        da[lat_name].values
    )

    lon_mask = (
        (lon_values >= lon_min)
        &
        (lon_values <= lon_max)
    )

    lat_mask = (
        (lat_values >= lat_min)
        &
        (lat_values <= lat_max)
    )

    lon_idx = np.where(
        lon_mask
    )[0]

    lat_idx = np.where(
        lat_mask
    )[0]

    if (
        len(lon_idx) == 0
        or
        len(lat_idx) == 0
    ):

        raise ValueError(
            "La región seleccionada no "
            "intersecta la grilla del NetCDF."
        )

    return da.isel(
        {
            lon_name: lon_idx,
            lat_name: lat_idx,
        }
    )


# ============================================================
# CONFIGURACIÓN QUIVER
# ============================================================

def get_quiver_style(
    map_extent,
    lon
):

    lon_span = abs(
        map_extent[1]
        -
        map_extent[0]
    )

    lat_span = abs(
        map_extent[3]
        -
        map_extent[2]
    )

    map_span = max(
        lon_span,
        lat_span
    )

    if map_span >= 50:

        step = max(
            1,
            int(
                len(lon) / 35
            )
        )

        quiver_scale = 250
        quiver_width = 0.0022

    elif map_span >= 25:

        step = max(
            1,
            int(
                len(lon) / 28
            )
        )

        quiver_scale = 150
        quiver_width = 0.0028

    elif map_span >= 12:

        step = max(
            1,
            int(
                len(lon) / 22
            )
        )

        quiver_scale = 75
        quiver_width = 0.0038

    else:

        step = max(
            1,
            int(
                len(lon) / 16
            )
        )

        quiver_scale = 45
        quiver_width = 0.0045

    return (
        step,
        quiver_scale,
        quiver_width,
    )


# ============================================================
# MIN / MAX REALES
# ============================================================

def get_real_min_max(
    values
):

    clean_values = values[
        np.isfinite(values)
    ]

    if clean_values.size == 0:

        raise ValueError(
            "No hay valores numéricos "
            "válidos para graficar."
        )

    vmin = float(
        np.nanmin(
            clean_values
        )
    )

    vmax = float(
        np.nanmax(
            clean_values
        )
    )

    if np.isclose(
        vmin,
        vmax
    ):

        delta = (
            abs(vmax) * 0.05
            if vmax != 0
            else 1.0
        )

        vmin -= delta
        vmax += delta

    return (
        vmin,
        vmax,
    )


# ============================================================
# GENERACIÓN DEL MAPA
# ============================================================

def plot_map(
    pp_data,
    u,
    v,
    speed,
    title,
    map_extent,
    pp_cmap_name,
    wind_cmap_name,
    quiver_edge_color,
    legend_text_color,
    title_color,
    title_fontsize,
    title_fontfamily,
    title_fontweight,
):

    # --------------------------------------------------------
    # Recorte al rectángulo geográfico seleccionado
    # --------------------------------------------------------

    pp_plot = crop_dataarray_to_extent(
        pp_data,
        map_extent
    )

    u_plot = crop_dataarray_to_extent(
        u,
        map_extent
    )

    v_plot = crop_dataarray_to_extent(
        v,
        map_extent
    )

    speed_plot = crop_dataarray_to_extent(
        speed,
        map_extent
    )

    lon, lat = (
        get_lon_lat_from_dataarray(
            pp_plot
        )
    )

    # --------------------------------------------------------
    # Figura
    # --------------------------------------------------------

    fig = plt.figure(
        figsize=(12, 10)
    )

    ax = plt.axes(
        projection=ccrs.PlateCarree()
    )

    ax.set_extent(
        map_extent,
        crs=ccrs.PlateCarree()
    )

    # --------------------------------------------------------
    # Valores de la región seleccionada
    # --------------------------------------------------------

    pp_values = (
        pp_plot.values
    )

    speed_values = (
        speed_plot.values
    )

    pp_vmin, pp_vmax = (
        get_real_min_max(
            pp_values
        )
    )

    wind_vmin, wind_vmax = (
        get_real_min_max(
            speed_values
        )
    )

    # --------------------------------------------------------
    # Precipitación
    # --------------------------------------------------------

    pp_levels = np.linspace(
        pp_vmin,
        pp_vmax,
        32
    )

    pp_cmap = plt.get_cmap(
        pp_cmap_name
    )

    wind_cmap = plt.get_cmap(
        wind_cmap_name
    )

    pp_norm = PowerNorm(
        gamma=0.30,
        vmin=pp_vmin,
        vmax=pp_vmax,
    )

    cf = ax.contourf(
        lon,
        lat,
        pp_values,
        levels=pp_levels,
        cmap=pp_cmap,
        norm=pp_norm,
        transform=ccrs.PlateCarree(),
        extend="neither",
    )

    # --------------------------------------------------------
    # Viento
    # --------------------------------------------------------

    (
        step,
        quiver_scale,
        quiver_width,
    ) = get_quiver_style(
        map_extent=map_extent,
        lon=lon,
    )

    wind_speed_sub = (
        speed_plot.values[
            ::step,
            ::step
        ]
    )

    q = ax.quiver(

        lon[::step],

        lat[::step],

        u_plot.values[
            ::step,
            ::step
        ],

        v_plot.values[
            ::step,
            ::step
        ],

        wind_speed_sub,

        cmap=wind_cmap,

        norm=Normalize(
            vmin=wind_vmin,
            vmax=wind_vmax
        ),

        transform=ccrs.PlateCarree(),

        scale=quiver_scale,

        width=quiver_width,

        headwidth=3.5,

        headlength=4.5,

        edgecolor=quiver_edge_color,

        linewidth=0.25,
    )

    # --------------------------------------------------------
    # Cartografía
    # --------------------------------------------------------

    ax.coastlines(
        linewidth=0.8
    )

    ax.add_feature(
        cfeature.BORDERS,
        linewidth=0.6
    )

    ax.add_feature(
        cfeature.LAND,
        facecolor="none",
        edgecolor="black",
        linewidth=0.3
    )

    gl = ax.gridlines(
        draw_labels=True,
        linewidth=0.3,
        alpha=0.5
    )

    gl.top_labels = False
    gl.right_labels = False

    # --------------------------------------------------------
    # Barra de precipitación
    # --------------------------------------------------------

    cbar_pp = plt.colorbar(
        cf,
        ax=ax,
        orientation="horizontal",
        pad=0.08,
        shrink=0.78,
    )

    cbar_pp.set_label(
        (
            "Precipitación acumulada estacional (mm)"
            f" | min: {pp_vmin:.2f}"
            f" - max: {pp_vmax:.2f}"
        ),
        color=legend_text_color,
    )

    cbar_pp.ax.tick_params(
        colors=legend_text_color
    )

    # --------------------------------------------------------
    # Barra de viento
    # --------------------------------------------------------

    cbar_wind = plt.colorbar(
        q,
        ax=ax,
        orientation="vertical",
        pad=0.03,
        shrink=0.72,
    )

    cbar_wind.set_label(
        (
            "Velocidad del viento (m/s)"
            f" | min: {wind_vmin:.2f}"
            f" - max: {wind_vmax:.2f}"
        ),
        color=legend_text_color,
    )

    cbar_wind.ax.tick_params(
        colors=legend_text_color
    )

    # --------------------------------------------------------
    # Título
    # --------------------------------------------------------

    ax.set_title(
        title,
        fontsize=title_fontsize,
        fontfamily=title_fontfamily,
        fontweight=title_fontweight,
        color=title_color,
    )

    return fig


# ============================================================
# CARGA DE ARCHIVOS
# ============================================================

pp_file = st.file_uploader(
    "Sube archivo NetCDF de precipitación",
    type=["nc"]
)

wind_file = st.file_uploader(
    "Sube archivo NetCDF de viento",
    type=["nc"]
)


# ============================================================
# PROCESAMIENTO PRINCIPAL
# ============================================================

if pp_file and wind_file:

    try:

        # ----------------------------------------------------
        # Abrir NetCDF
        # ----------------------------------------------------

        ds_pp = normalize_time(
            open_nc(
                pp_file
            )
        )

        ds_wind = normalize_time(
            open_nc(
                wind_file
            )
        )

        # ----------------------------------------------------
        # Variable precipitación
        # ----------------------------------------------------

        pp_var = guess_pp_variable(
            ds_pp
        )

        # ----------------------------------------------------
        # Guardar metadata ORIGINAL antes de convertir
        # ----------------------------------------------------

        raw_pp_attrs = dict(
            ds_pp[
                pp_var
            ].attrs
        )

        raw_pp_encoding = dict(
            ds_pp[
                pp_var
            ].encoding
        )

        # ----------------------------------------------------
        # Convertir precipitación a mm
        # ----------------------------------------------------

        ds_pp = prepare_pp_dataset(
            ds_pp,
            pp_var
        )

        # ----------------------------------------------------
        # Variables viento
        # ----------------------------------------------------

        u_var, v_var = (
            guess_wind_variables(
                ds_wind
            )
        )

        # ----------------------------------------------------
        # Validación
        # ----------------------------------------------------

        (
            pp_months,
            wind_months,
            common_months,
        ) = check_compatibility(
            ds_pp,
            ds_wind
        )

        st.success(
            "Archivos NetCDF cargados "
            "y validados correctamente."
        )

        st.write(
            f"Variable de precipitación detectada: `{pp_var}`"
        )

        st.write(
            "Unidad utilizada internamente "
            "para precipitación: `mm`"
        )

        st.write(
            f"Variables de viento detectadas: "
            f"`{u_var}` y `{v_var}`"
        )


        # ====================================================
        # DIAGNÓSTICO NETCDF
        # ====================================================

        with st.expander(
            "Diagnóstico NetCDF"
        ):

            st.write(
                "### Atributos originales "
                "de precipitación"
            )

            st.json(
                raw_pp_attrs
            )

            st.write(
                "### Encoding original "
                "de precipitación"
            )

            safe_encoding = {

                k: str(v)

                for k, v
                in raw_pp_encoding.items()

                if k in [
                    "source",
                    "original_shape",
                    "dtype",
                    "scale_factor",
                    "add_offset",
                    "_FillValue",
                ]
            }

            st.json(
                safe_encoding
            )

            st.write(
                "### Dimensiones"
            )

            st.json(
                {
                    key: int(value)
                    for key, value
                    in ds_pp[
                        pp_var
                    ].sizes.items()
                }
            )

            # -----------------------------------------------
            # Tiempo
            # -----------------------------------------------

            st.write(
                "### Tiempos disponibles"
            )

            time_values = (
                pd.to_datetime(
                    ds_pp.time.values
                )
            )

            st.write(
                "Primer tiempo:",
                time_values.min()
            )

            st.write(
                "Último tiempo:",
                time_values.max()
            )

            st.write(
                "Cantidad de pasos:",
                len(time_values)
            )

            # -----------------------------------------------
            # Pixel central
            # -----------------------------------------------

            st.write(
                "### Pixel de prueba"
            )

            lat_name, lon_name = (
                get_lat_lon_names(
                    ds_pp
                )
            )

            pixel = (
                ds_pp[
                    pp_var
                ]
                .isel(
                    {
                        lat_name:
                            len(
                                ds_pp[
                                    lat_name
                                ]
                            ) // 2,

                        lon_name:
                            len(
                                ds_pp[
                                    lon_name
                                ]
                            ) // 2,
                    }
                )
            )

            df_pixel = (
                pixel
                .to_dataframe()
                .reset_index()
            )

            st.dataframe(
                df_pixel.head(20),
                use_container_width=True
            )


        # ====================================================
        # OPCIONES PRINCIPALES
        # ====================================================

        col1, col2, col3 = (
            st.columns(3)
        )

        with col1:

            period = st.selectbox(
                "Periodo",
                [
                    "Verano DJF",
                    "Invierno JJA",
                ]
            )

        with col2:

            mode = st.selectbox(
                "Tipo de mapa",
                [
                    "Mapa por año",
                    "Mapa promedio de años",
                ]
            )

        with col3:

            selected_region = (
                st.selectbox(
                    "Región",
                    list(
                        COUNTRY_EXTENTS.keys()
                    )
                )
            )


        # ====================================================
        # PERSONALIZACIÓN
        # ====================================================

        st.divider()

        st.subheader(
            "Personalización del mapa"
        )

        col_color1, col_color2 = (
            st.columns(2)
        )

        with col_color1:

            pp_cmap_base = (
                st.selectbox(
                    "Paleta de precipitación",
                    AVAILABLE_CMAPS,
                    index=0,
                )
            )

            invert_pp_cmap = (
                st.checkbox(
                    "Invertir paleta de precipitación",
                    value=False,
                )
            )

        with col_color2:

            wind_cmap_base = (
                st.selectbox(
                    "Paleta de viento",
                    AVAILABLE_CMAPS,
                    index=1,
                )
            )

            invert_wind_cmap = (
                st.checkbox(
                    "Invertir paleta de viento",
                    value=False,
                )
            )

        pp_cmap_name = (
            f"{pp_cmap_base}_r"
            if invert_pp_cmap
            else pp_cmap_base
        )

        wind_cmap_name = (
            f"{wind_cmap_base}_r"
            if invert_wind_cmap
            else wind_cmap_base
        )


        # ====================================================
        # ESTILO
        # ====================================================

        (
            col_style1,
            col_style2,
            col_style3,
            col_style4,
        ) = st.columns(4)

        with col_style1:

            quiver_edge_color = (
                st.color_picker(
                    "Borde de flechas",
                    value="#000000"
                )
            )

        with col_style2:

            legend_text_color = (
                st.color_picker(
                    "Color de leyendas",
                    value="#000000"
                )
            )

        with col_style3:

            title_color = (
                st.color_picker(
                    "Color del título",
                    value="#000000"
                )
            )

        with col_style4:

            title_fontsize = (
                st.slider(
                    "Tamaño del título",
                    8,
                    32,
                    14,
                    1
                )
            )

        col_title1, col_title2 = (
            st.columns(2)
        )

        with col_title1:

            title_fontfamily = (
                st.selectbox(
                    "Tipo de letra del título",
                    [
                        "DejaVu Sans",
                        "DejaVu Serif",
                        "Arial",
                        "Times New Roman",
                        "Calibri",
                        "Verdana",
                        "Georgia",
                    ],
                )
            )

        with col_title2:

            title_fontweight = (
                st.selectbox(
                    "Grosor del título",
                    [
                        "normal",
                        "bold",
                        "semibold",
                        "light",
                    ],
                    index=1,
                )
            )


        # ====================================================
        # AÑOS VÁLIDOS
        # ====================================================

        valid_years = (
            get_available_years(
                pp_months=pp_months,
                wind_months=wind_months,
                period=period,
            )
        )

        if not valid_years:

            st.error(
                "No existen años completos "
                "para el periodo seleccionado."
            )

            st.stop()


        # ====================================================
        # SELECCIÓN TEMPORAL
        # ====================================================

        selected_year = None
        selected_years_range = None

        if mode == "Mapa por año":

            selected_year = (
                st.selectbox(
                    "Año",
                    valid_years,
                    index=(
                        len(valid_years)
                        - 1
                    ),
                )
            )

        else:

            selected_years_range = (
                st.slider(
                    "Periodo de años para calcular el promedio",
                    min_value=min(
                        valid_years
                    ),
                    max_value=max(
                        valid_years
                    ),
                    value=(
                        min(valid_years),
                        max(valid_years),
                    ),
                    step=1,
                )
            )


        # ====================================================
        # GENERAR MAPA
        # ====================================================

        if st.button(
            "Generar mapa"
        ):

            with st.spinner(
                "Espere un momento por favor."
            ):

                map_extent = (
                    COUNTRY_EXTENTS[
                        selected_region
                    ]
                )

                # ============================================
                # MAPA POR AÑO
                # ============================================

                if mode == "Mapa por año":

                    pp_data = (
                        calculate_precip_accumulated_one_year(
                            ds_pp=ds_pp,
                            pp_var=pp_var,
                            period=period,
                            year=selected_year,
                        )
                    )

                    (
                        u,
                        v,
                        speed,
                    ) = (
                        calculate_wind_average_one_year(
                            ds_wind=ds_wind,
                            u_var=u_var,
                            v_var=v_var,
                            period=period,
                            year=selected_year,
                        )
                    )

                    title = (
                        f"{selected_region} - "
                        f"{period} {selected_year}\n"
                        "Precipitación acumulada estacional "
                        "+ viento promedio"
                    )

                    file_name = (
                        f"mapa_"
                        f"{selected_region.replace(' ', '_')}_"
                        f"pp_acumulada_"
                        f"{period.replace(' ', '_')}_"
                        f"{selected_year}.png"
                    )

                # ============================================
                # PROMEDIO DE AÑOS
                # ============================================

                else:

                    (
                        start_year,
                        end_year,
                    ) = (
                        selected_years_range
                    )

                    years_for_mean = [

                        year

                        for year
                        in valid_years

                        if (
                            start_year
                            <= year
                            <= end_year
                        )
                    ]

                    if not years_for_mean:

                        st.error(
                            "No existen años válidos "
                            "dentro del periodo seleccionado."
                        )

                        st.stop()

                    pp_data = (
                        calculate_precip_accumulated_mean_years(
                            ds_pp=ds_pp,
                            pp_var=pp_var,
                            period=period,
                            years=years_for_mean,
                        )
                    )

                    (
                        u,
                        v,
                        speed,
                    ) = (
                        calculate_wind_average_mean_years(
                            ds_wind=ds_wind,
                            u_var=u_var,
                            v_var=v_var,
                            period=period,
                            years=years_for_mean,
                        )
                    )

                    title = (
                        f"{selected_region} - {period}\n"
                        f"Promedio "
                        f"{min(years_for_mean)}"
                        f"-"
                        f"{max(years_for_mean)}\n"
                        "Precipitación acumulada estacional "
                        "+ viento promedio"
                    )

                    file_name = (
                        f"mapa_promedio_"
                        f"{selected_region.replace(' ', '_')}_"
                        f"pp_acumulada_"
                        f"{period.replace(' ', '_')}_"
                        f"{min(years_for_mean)}_"
                        f"{max(years_for_mean)}.png"
                    )


                # ============================================
                # RECORTE PARA ESTADÍSTICAS
                # ============================================

                pp_region = (
                    crop_dataarray_to_extent(
                        pp_data,
                        map_extent
                    )
                )

                speed_region = (
                    crop_dataarray_to_extent(
                        speed,
                        map_extent
                    )
                )


                # ============================================
                # ESTADÍSTICAS REGIONALES
                # ============================================

                st.write(
                    "PP acumulada mínima "
                    "en región visible (mm):",
                    float(
                        np.nanmin(
                            pp_region.values
                        )
                    ),
                )

                st.write(
                    "PP acumulada máxima "
                    "en región visible (mm):",
                    float(
                        np.nanmax(
                            pp_region.values
                        )
                    ),
                )

                st.write(
                    "Velocidad mínima del viento "
                    "en región visible (m/s):",
                    float(
                        np.nanmin(
                            speed_region.values
                        )
                    ),
                )

                st.write(
                    "Velocidad máxima del viento "
                    "en región visible (m/s):",
                    float(
                        np.nanmax(
                            speed_region.values
                        )
                    ),
                )


                # ============================================
                # MAPA
                # ============================================

                fig = plot_map(

                    pp_data=pp_data,

                    u=u,

                    v=v,

                    speed=speed,

                    title=title,

                    map_extent=map_extent,

                    pp_cmap_name=pp_cmap_name,

                    wind_cmap_name=wind_cmap_name,

                    quiver_edge_color=quiver_edge_color,

                    legend_text_color=legend_text_color,

                    title_color=title_color,

                    title_fontsize=title_fontsize,

                    title_fontfamily=title_fontfamily,

                    title_fontweight=title_fontweight,
                )

                st.pyplot(
                    fig
                )


                # ============================================
                # DESCARGA PNG
                # ============================================

                buffer = io.BytesIO()

                fig.savefig(
                    buffer,
                    format="png",
                    dpi=300,
                    bbox_inches="tight",
                )

                buffer.seek(0)

                st.download_button(

                    label="Descargar mapa PNG",

                    data=buffer,

                    file_name=file_name,

                    mime="image/png",
                )

                plt.close(fig)


    except Exception as e:

        st.error(
            f"Error: {e}"
        )


else:

    st.info(
        "Sube ambos archivos NetCDF "
        "para iniciar el procesamiento."
    )


# ============================================================
# OCULTAR ENLACE STREAMLIT
# ============================================================

html("""
<script>
window.top.document
.querySelectorAll(`[href*="streamlit.io"]`)
.forEach(
    e => e.setAttribute(
        "style",
        "display: none;"
    )
);
</script>
""")
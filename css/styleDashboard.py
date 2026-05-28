
color_fondo_dash="""
<style>


# /* 1. Oculta todo el contenido del header */
# [data-testid="stHeader"] * {
#     visibility: hidden !important;
#     background:transparent;
# }

# /* 2. Muestra específicamente el botón de expandir la sidebar */
# [data-testid="stExpandSidebarButton"] {
#     visibility: visible !important;
#     position: fixed !important;
#     top: 15px !important;
#     left: 15px !important;
#     z-index: 9999 !important;
#     background: linear-gradient(to left, #2D9CDB, #1E3A8A);
#     border-radius: 50% !important;
#     padding: 6px !important;
#     box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25) !important;
# }

# /* 3. Tip adicional para asegurar visibilidad incluso si se hereda invisibilidad */
# [data-testid="stExpandSidebarButton"], 
# [data-testid="stExpandSidebarButton"] * {
#     visibility: visible !important;
#     opacity: 1 !important;
# }


/* 1. El header queda transparente, sin sombra ni fondo */
[data-testid="stHeader"] {
    background-color: transparent !important;
    box-shadow: none !important;
    z-index: 1 !important;
}

[data-testid="stToolbarActions"] {
visibility:hidden !important;
}

[data-testid="stMainMenu"] {
visibility:hidden !important;
}




[data-testid="stSidebar"]{
background: #e3e9f3;
}

/* Estilo base para los enlaces del sidebar */
[data-testid="stSidebarNavLink"] {
    display: flex; /* Asegura alineación horizontal */
    align-items: center; /* Centra los íconos y texto verticalmente */
    color: #2b2b2b  !important; /* Texto blanco */
    font-family: "Arial", sans-serif; /* Fuente profesional */
    font-weight: normal; /* Texto en normal */
    padding: 3px 3px 3px 3px ; /* Espaciado interno */
    margin: 20px 20px 0px 20px; /* Margen externo */
    border-radius: 8px; /* Bordes redondeados */
    text-decoration: none; /* Sin subrayado */
    background: rgba(45, 156, 219, 0.08); /* Fondo translúcido */
    transition: all 0.3s ease; /* Suavidad en las transiciones */
    cursor: pointer; /* Cambia el cursor */
}

/* Hover: Interactividad al pasar el cursor */
[data-testid="stSidebarNavLink"]:hover {
    background: rgba(45, 156, 219, 0.18); /* Fondo más claro */
    color: #1B74C6 !important; /* Texto rojo */
}

/* Estilo del enlace activo */
[data-testid="stSidebarNavLink"][aria-current="page"] {
    background: linear-gradient(to right,#1E3A8A, #2D9CDB); /* Fondo degradado */
    color: #FFFFFF !important; /* Texto blanco */
}

/* Estilo para el texto dentro del enlace */
[data-testid="stSidebarNavLink"] span:last-child {
    color: inherit; /* Hereda el color del enlace */
    font-size: 14px; /* Tamaño del texto */
    font-weight: normal; /* Normal*/
    overflow: hidden; /* Evita desbordamientos */
    text-overflow: ellipsis; /* Añade puntos suspensivos si el texto es muy largo */
    white-space: nowrap; /* Evita que el texto se divida en varias líneas */
}

/* Imágenes */
[data-testid="stImage"] {
    display: flex;
    justify-content: center ;
    padding: 5px;
    background: rgba(255, 255, 255, 0.05);
    border-radius: 5px;
    transition: all 0.3s ease;
}

[data-testid="stImage"] img {
    border-radius: 5px;
    max-width: 100%;
    height: auto;
    transition: transform 0.3s ease, box-shadow 0.3s ease;
}

[data-testid="stImage"]:hover {
    cursor: pointer;
}

[data-testid="stImage"] img:hover {
    transform: scale(0.95);
    box-shadow: 0px 6px 12px rgba(0, 0, 0, 0.2);
}





[data-testid="stHeadingWithActionElements"] {
    display: flex;
    align-items: center;
    justify-content: space-between;
    /*background: linear-gradient(to bottom, #E8F2FC, #DCE7F3);*/
    background: linear-gradient(to bottom, #f9f9f9, #f0f0f0, #e0e0e0, #d0d0d0, #c0c0c0);

    padding: 10px 20px;
    border-radius: 8px;
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
    margin: 15px 0;
    transition: all 0.3s ease-in-out;
}
[data-testid="stHeadingWithActionElements"]:hover {
    /*background: linear-gradient(to bottom, #DCE7F3, #CBD6E2);*/
    box-shadow: 0 6px 12px rgba(0, 0, 0, 0.15);
    transform: translateY(-2px);
}
[data-testid="stHeadingWithActionElements"] h1 {
    font-family: "Arial", sans-serif;
    font-size: 28px;
    color: #003366;
    /*color:#ffffff;*/

    font-weight: bold;
    margin: 0;
    line-height: 1.2;
    transition: color 0.3s ease;
}
[data-testid="stHeadingWithActionElements"] h1:hover {
    /*color: #0B60A7;*/
    cursor: pointer;
}
[data-testid="stHeadingWithActionElements"] button,
[data-testid="stHeadingWithActionElements"] a {
    /*background: #0B60A7;*/
    color: white;
    border: none;
    border-radius: 5px;
    padding: 5px 10px;
    font-size: 14px;
    font-weight: bold;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
    transition: all 0.3s ease;
    text-decoration: none;
}
[data-testid="stHeadingWithActionElements"] button:hover,
[data-testid="stHeadingWithActionElements"] a:hover {
    /*background: #004080;*/
    transform: scale(1.05);
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.3);
    cursor: pointer;
}





[data-testid="stCaptionContainer"] {
    /*background: linear-gradient(to bottom, #F5F7FA, #E8F2FC);*/
    border-left: 4px solid #0B60A7;
    border-radius: 8px;
    padding: 10px 15px;
    margin: 10px 0;
    box-shadow: 0px 2px 6px rgba(0, 0, 0, 0.1);
    transition: all 0.3s ease-in-out;
    /*font-family: "Arial", sans-serif;*/
    font-size: 14px;
    color: #333333;
    line-height: 1.5;
}
[data-testid="stCaptionContainer"]:hover {
    /*background: linear-gradient(to bottom, #E8F2FC, #DCE7F3);*/
    border-left: 4px solid #004080;
    box-shadow: 0px 4px 8px rgba(0, 0, 0, 0.15);
    transform: translateY(-2px);
    cursor: default;
}
[data-testid="stCaptionContainer"] p {
    margin: 0;
    color: #004080;
    /*font-weight: bold;*/
    font-size: 14.5px;
}





/* Contenedor general del expander */
[data-testid="stExpander"] {
    background: #f8f9fa !important;
    border: 1px solid #d1d9e6 !important;
    border-radius: 16px !important;
    box-shadow: 0 6px 20px rgba(0, 0, 0, 0.12);
    margin: 5px 0 !important;
    padding: 0px !important;
    overflow: hidden !important;
}

/* Título con degradado más notorio */
[data-testid="stExpander"] summary {
    
    background: linear-gradient(to bottom, #f9f9f9, #f0f0f0, #e0e0e0, #d0d0d0, #c0c0c0);

    color:#003366 !important;
    padding: 18px 24px;
    font-size: 17px;
    font-weight: bold;
    font-family: "Segoe UI", sans-serif;
    border-bottom: 1px solid rgba(255,255,255,0.2);
    transition: background 0.3s ease;
    border-top-left-radius: 16px;
    border-top-right-radius: 16px;
    display: flex;
    align-items: center;
}

/* Hover con variación del degradado */
[data-testid="stExpander"] summary:hover {
    /*background: linear-gradient(to right, #09457c, #001A33);*/
    cursor: pointer;
}

/* Estilo del ícono de expansión (SVG) */
[data-testid="stExpanderToggleIcon"] {
    color: white !important;
    width: 20px;
    height: 20px;
    margin-left: auto; /* Empuja el ícono a la derecha */
    transition: transform 0.3s ease;
}

/* Gira el ícono cuando el expander está abierto */
[data-testid="stExpander"] details[open] [data-testid="stExpanderToggleIcon"] {
    transform: rotate(180deg);
}

/* Contenido expandido */
[data-testid="stExpanderDetails"] {
    background-color: #ffffff;
    padding: 20px 25px !important;
    font-family: "Segoe UI", sans-serif;
    font-size: 14px;
    color: #2c3e50;
}

/* Tabla dentro del expander */
[data-testid="stExpanderDetails"] table {
    border-collapse: collapse;
    width: 100%;
    border-radius: 10px;
    overflow: hidden;
    font-size: 13px;
}

/* Cabecera de tabla */
[data-testid="stExpanderDetails"] thead tr {
    background-color: #0B60A7;
    color: white;
}

/* Celdas */
[data-testid="stExpanderDetails"] td,
[data-testid="stExpanderDetails"] th {
    padding: 10px 8px;
    text-align: left;
    border-bottom: 1px solid #e0e0e0;
}

/* Botón dentro del expander (como el de “Limpiar D.U.A”) */
[data-testid="stExpanderDetails"] button {
    background: #0B60A7;
    color: white;
    font-weight: bold;
    border: none;
    border-radius: 8px;
    padding: 10px 18px;
    box-shadow: 0 4px 10px rgba(0,0,0,0.1);
    transition: background 0.3s ease;
}

[data-testid="stExpanderDetails"] button:hover {
    background: #004080;
    cursor: pointer;
}

/* Responsive */
@media screen and (max-width: 768px) {
    [data-testid="stExpander"] summary {
        font-size: 15px;
        padding: 14px 18px;
    }

    [data-testid="stExpanderDetails"] {
        padding: 15px;
    }

    [data-testid="stExpanderDetails"] table {
        font-size: 12px;
    }
}





div[data-testid="stAlertContainer"] {
    background: linear-gradient(to left, #10d5e8, #0B60A7);  /* Degradado horizontal */
    color: #ffffff !important;
    font-family: "Arial", sans-serif;
    padding: 14px 22px;
    border-radius: 12px;
    border-left: 5px solid #10d5e8;
    margin: 1px 0;

    /* 🎯 Efecto 3D */
    box-shadow:
        0 2px 4px rgba(0, 0, 0, 0.1),
        0 6px 12px rgba(0, 0, 0, 0.15),
        inset 0 1px 0 rgba(255, 255, 255, 0.4);
    transition: all 0.3s ease;
}

/* Hover con elevación */
div[data-testid="stAlertContainer"]:hover {
    transform: translateY(-2px);
    box-shadow:
        0 4px 8px rgba(0, 0, 0, 0.15),
        0 8px 16px rgba(0, 0, 0, 0.2),
        inset 0 1px 0 rgba(255, 255, 255, 0.5);
    cursor: default;
}

/* Íconos internos blancos */
div[data-testid="stAlertContainer"] svg {
    fill: white !important;
}





  [data-testid="stMainBlockContainer"] {
   background: white;
    padding: 30px 60px 130px 60px !important;
    /*margin: 20px !important;*/
    border-radius: 0px 0px 16px 16px !important;
    box-shadow: 0 8px 30px rgba(0, 0, 0, 0.08);
    max-width: 100% !important;
    transition: all 0.3s ease-in-out;
    font-family: "Segoe UI", sans-serif;
} 


</style>


"""
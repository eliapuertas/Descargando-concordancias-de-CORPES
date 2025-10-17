import os
import time
import logging
import pyautogui
import re
import argparse
import platform
import shutil
import pandas as pd
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException, NoAlertPresentException
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager
from webdriver_manager.microsoft import EdgeChromiumDriverManager
from itertools import zip_longest
from datetime import date, datetime


# Primera regex para dividir la línea en dos bloques
REGEX_PATTERN_1 = re.compile(r'(?<=\d)\s{2,}')
# Segunda regex para separar el tema y la publicación
REGEX_PATTERN_2 = re.compile(r'\s(?=\d+\.[A-Z].+)')
# Tercera regex para el año y el autor
REGEX_PATTERN_3 = re.compile(r'\s{2,}')
# Cuarta regex para obtener el tema y la publicación por separado
REGEX_PATTERN_4 = re.compile(r'\s(?=[A-Z])')

def download_driver(navegador:str, drivers_dir:Path) -> Path:
    """
    Descargamos el driver del navegador indicado usando webdriver-manager
    y lo COPIAMOS en el directorio especificado
    """
    current_platform = platform.system().lower()
    if navegador =='chrome':
        downloaded_path =  ChromeDriverManager().install()
        # Definimos el nombre correcto del archivo en funicón del OS
        target_file = "chromedriver.exe" if current_platform == "windows" else "chromedriver"
        target_path = drivers_dir / target_file
    
    elif navegador == 'firefox':
        downloaded_path = GeckoDriverManager().install()
        # Definimos el nombre correcto del archivo en función del OS
        target_file = "geckodriver.exe" if current_platform == "windows" else "geckodriver"
        target_path = drivers_dir / target_file
    
    elif navegador == 'edge':
        downloaded_path = EdgeChromiumDriverManager().install()
        # Definimos el nombre correcto del archivo en función del OS
        target_file = "msedgedriver.exe" if current_platform == "windows" else "msedgedriver"
        target_path = drivers_dir / target_file
    
    # Ahora, con independencia del OS vamos a copiar lo descargado en el 
    # dir objetivo en caso de que no exista
    if not target_path.exists():
        shutil.copy2(downloaded_path, target_path)
    return target_path

def configurar_driver(navegador):
    try:
        logging.info(f"Configurando driver para {navegador}...")
        # Determinamos el directorio base (donde se encuentra este script)
        base_dir = Path(__file__).resolve().parent
        # Obtenemos el SO
        current_platform = platform.system().lower()
        
        # Directorio específico para los drivers
        drivers_dir = base_dir / 'drivers' / current_platform
        drivers_dir.mkdir(parents=True, exist_ok=True)

        if navegador.lower() == 'chrome':
            driver_file = "chromedriver.exe" if current_platform == "windows" else "chromedriver"
            driver_path = drivers_dir / driver_file
            if driver_path.exists():
                logging.info(f"El driver para {navegador} ya existe en: {driver_path}")
                downloaded_driver = driver_path
            else:
                logging.info(f"No se encontró el driver para {navegador} en {drivers_dir}. Descargando...")
                downloaded_driver = download_driver(navegador, drivers_dir)
                logging.info(f"Driver descargado en: {downloaded_driver}")

            if not downloaded_driver.exists():
                raise FileNotFoundError(f"ChromeDriver no encontrado en {downloaded_driver}")
            
            options = webdriver.ChromeOptions()
            options.add_argument("--start-maximized")
            service = ChromeService(executable_path=downloaded_driver)
            driver = webdriver.Chrome(service=service, options=options)

        elif navegador.lower() == 'firefox':
            driver_file = "geckodriver.exe" if current_platform == "windows" else "geckodriver"
            driver_path = drivers_dir / driver_file
            if driver_path.exists():
                logging.info(f"El driver para {navegador} ya existe en: {driver_path}")
                downloaded_driver = driver_path
            else:
                logging.info(f"No se encontró el driver para {navegador} en {drivers_dir}. Descargando...")
                downloaded_driver = download_driver(navegador, drivers_dir)
                logging.info(f"Driver descargado en: {downloaded_driver}")

            if not downloaded_driver.exists():
                raise FileNotFoundError(f"ChromeDriver no encontrado en {downloaded_driver}")
            
            options = webdriver.FirefoxOptions()
            service = FirefoxService(executable_path=downloaded_driver)
            driver = webdriver.Firefox(service=service, options=options)
            driver.maximize_window()  # Maximizar la ventana de Firefox

        elif navegador.lower() == 'edge':
            driver_file = "msedgedriver.exe" if current_platform == "windows" else "msedgedriver"
            driver_path = drivers_dir / driver_file
            if driver_path.exists():
                logging.info(f"El driver para {navegador} ya existe en: {driver_path}")
                downloaded_driver = driver_path
            else:
                logging.info(f"No se encontró el driver para {navegador} en {drivers_dir}. Descargando...")
                downloaded_driver = download_driver(navegador, drivers_dir)
                logging.info(f"Driver descargado en: {downloaded_driver}")

            if not downloaded_driver.exists():
                raise FileNotFoundError(f"ChromeDriver no encontrado en {downloaded_driver}")
            
            options = webdriver.EdgeOptions()
            options.add_argument("--start-maximized")
            service = EdgeService(executable_path=downloaded_driver)
            driver = webdriver.Edge(service=service, options=options)

        else:
            raise ValueError(f"Navegador no soportado: {navegador}")
        
        driver.browser_name = navegador.capitalize()
        return driver

    except Exception as e:
        logging.error(f"Error en configurar_driver: {e}")
        raise

def parsear_concordancia(ocurrencia: str) -> list[str]:
    """
    Dado un string que contiene las columnas que debemos extraer,
    utilizamos varias regex para obtener una lista de strings.
    Devuelve siempre los resultados, aunque falten o sobren columnas.
    """
    if not ocurrencia:
        return []

    # Separación inicial por "**"
    first_processing = ocurrencia.split("**")
    if len(first_processing) != 2:
        return [ocurrencia.strip()]

    num_concord = first_processing[0].strip()
    year_autor = first_processing[1].strip()

    result = []
    result.extend(REGEX_PATTERN_1.split(num_concord))

    # Separación año / autor
    second_processing = REGEX_PATTERN_2.split(year_autor)
    if len(second_processing) == 2:
        year_autor_2 = second_processing[0].strip()
        topic_pub = second_processing[1].strip()
    else:
        year_autor_2 = year_autor
        topic_pub = ""

    result.extend(REGEX_PATTERN_3.split(year_autor_2))

    # Separación título / país
    if topic_pub:
        partes = REGEX_PATTERN_4.split(topic_pub, maxsplit=1)
        result.extend(partes)
    else:
        result.append(topic_pub)

    # Rellenamos hasta 8 campos
    while len(result) < 8:
        result.append('_')

    titulo = result[4]

    # Buscamos el país
    pattern_pais_final = re.compile(
        r'\b([A-ZÁÉÍÓÚÑÜ]{2,}(?:\s+[A-ZÁÉÍÓÚÑÜ]{2,})*)\b(?=[\s\]\)\.\,\;\:\-]*$)',
        re.UNICODE
    )
    match_pais = pattern_pais_final.search(titulo)

    if not match_pais:
        posibles_mayus = re.findall(r'\b[A-ZÁÉÍÓÚÑÜ]{3,}\b', titulo)
        if posibles_mayus:
            candidato = posibles_mayus[-1]  # tomamos la última palabra en mayúsculas
            # Excluir números romanos
            if not re.fullmatch(
                r'I{1,3}|IV|V|VI{0,3}|IX|X|XI{0,3}|XV|XX|XXX|XL|L|LX|LXX|XC|C|CC|CCC|CD|D|DC|DCC|CM|M{1,4}',
                candidato
            ):
                match_pais = re.search(re.escape(candidato), titulo)

    # Separamos el título y el país
    if match_pais:
        posible_pais = match_pais.group(0).strip()
        # Eliminamos solo el país detectado del título
        result[4] = re.sub(r'\s*' + re.escape(posible_pais) + r'[\s\]\)\.\,\;\:\-]*', '', titulo).strip()

        if result[5] not in ['_', '']:
            result.insert(5, posible_pais)
            result = result[:8]
        else:
            result[5] = posible_pais

    return result[:8]

def extraer_concordancias(driver):
    """
    Vamos a extraer todas las concordancias que se han extraído para un 
    mismo resultado.
    Para cada concordancia extraemos un diccionario tal que:
    {
        n: Número
        concord: Concordancia devuelta
        fecha: Fecha
        autor: Autor
        titulo: Título
        pais: País
        tema: Tema
    }
    """
    # El primer paso es asegurarnos de que de verdad nos encontramos
    # en una página que recupera Concordancias y no Documentos, por ejemplo
    dropdown = driver.find_element(By.CSS_SELECTOR, "select[name='tipo1']")
    # Lo seleccionamos con Select
    select_obj = Select(dropdown)
    # Extraemos el tipo que está seleccionado
    selected = select_obj.first_selected_option.text
    if 'Concordancias' not in selected.strip():
        # Validamos el string
        raise ValueError('La página en la que nos encontramos no tiene concordancias')
    result = []
    # Tenemos que guardar un listado del ID de la concordancia
    id_concordancias = []
    # Iniciamos un bucle infinito:
    while True:
        # Paso 1, obtenemos el contenedor de las concordancias
        outer_element = driver.find_element(By.TAG_NAME, "tt")
        
        # Paso 2, extraemos las cabeceras de los resultados
        header_element = outer_element.find_element(By.TAG_NAME, 'b').text
        headers = re.sub('\s+', ' ', header_element).split(' ')
        
        # Paso 3, extraemos el texto de las concordancias MENOS el de los títulos
        concords = outer_element.text.replace(header_element, '').split('\n')

        # Paso 4, procesamos cada concordancia
        clean_concords = []
        for concord in concords:
            processed = parsear_concordancia(concord)
            if processed is not None and len(processed)>1:
                # Después de garantizar que la concordancia es una lista
                # extraemos el primer elemento, que es el número/ID
                # si el ID no existe:
                #     guardamos el ID y la propia concordancia
                # si el ID SÍ existe salimos de este bucle y no procesamos
                # más
                if processed[0] not in id_concordancias:
                    id_concordancias.append(processed[0])
                    clean_concords.append(processed)
                else:
                    break
            else:
                pass
        
        # Paso 5, creamos un diccionario con cada uno de los resultados
        # Y cada resultado lo incluimos en la lista que sera nuestro resultado final 
        for clean_concord in clean_concords:
            result.append({header:att for header,att in zip_longest(headers, clean_concord, fillvalue='_')})
        # Evaluamos la condición de salida: que no haya un botón de Siguiente
        # Recargamos la página:
        driver.execute_script("""
        window.onbeforeunload = null;
        window.addEventListener('beforeunload', e => e.stopImmediatePropagation(), true);
        """)
        driver.refresh()
        try:
            alert = driver.switch_to.alert
            alert.accept()
        except NoAlertPresentException:
            pass
        link_elements = driver.find_elements(By.CSS_SELECTOR, "td.texto a[href*='visualizar']")
        # Solo hay dos opciones con enlace <siguiente>
        siguientes = [element for element in link_elements if 'Siguiente' in element.text]
        if len(siguientes) > 0:
            siguientes[0].click()
            del link_elements
        else:
            # Borramos para evitar que los threads de selenium
            # se vuelvan locos
            del link_elements
            break
    return result

def guardar_resultados(resultados:list[dict], 
                       format:str='excel', 
                       output_path:Path=Path(__file__).resolve().parent)->None:
    """
    Una vez que ya hemos completado el parsing de la web vamos a guardar
    los resultados en dos posibles formatos: csv o excel
    
    Para ello crearemos un dataframe: los resultados no son más que una
    lista de resultados.
    
    Y después llamaremos al método correspondiente
    """
    if format not in ['excel','csv']:
        raise ValueError('Formato no reconocido.')
    if resultados is None or len(resultados) < 1:
        raise ValueError('No hay resultados para exportar')
    df = pd.DataFrame.from_records(resultados)
    # Crearemos una carpeta con los resultados de hoy
    today_str = date.today().strftime("%d-%m-%Y") 
    final_path = output_path / 'results' / today_str
    final_path.mkdir(parents=True, exist_ok=True)
    
    # Ahora guardamos en el formato especificado:
    if format == 'csv':
        file_name = datetime.now().strftime("%Y-%m-%d_%H-%M") + '.csv'
        df.to_csv(final_path/file_name)
    elif format == 'excel':
        file_name = datetime.now().strftime("%Y-%m-%d_%H-%M") + '.xlsx'
        df.to_excel(final_path/file_name)

def main():
    # Configuramos un CLI para poder ejecutar el navegador que queremos
    parser = argparse.ArgumentParser(description='Script para extraer coincidencias del CORDE.')
    parser.add_argument('-b', '--browser', 
                        action='store', 
                        default='firefox', 
                        type=str, 
                        choices=['chrome', 'firefox', 'edge'], 
                        help='Selecciona el navegador: chrome, firefox, edge.')
    parser.add_argument('-t', '--type', 
                        action='store', 
                        default='concord', 
                        type=str, 
                        choices=['concord', 'doc', 'par', 'agrup'], 
                        help='Selecciona el tipo de resultados que quieres extraer.')
    parser.add_argument('-f', '--format', 
                        action='store', 
                        default='excel', 
                        type=str, 
                        choices=['csv', 'excel'], 
                        help='Selecciona el fomato en el que se guardarán los resultados.')
    parser.add_argument("-o", "--output", 
                        type=Path, 
                        default=Path(__file__).resolve().parent, 
                        help="Directorio de salida para los resultados. Por defecto el directorio de instalación")
    parser.add_argument("-v", "--verbose", 
                        action="store_true", 
                        help="Ajusta el logging a INFO-level"
    )
    args = parser.parse_args()
    # Configruamos el logging
    log_level = logging.INFO if args.verbose else logging.WARNING
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s %(levelname)-8s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        force=True  # Python 3.8+: override any existing handlers
    )
    logging.info("Comenzando la ejecución del script.")


    navegador = args.browser.lower()
    driver = configurar_driver(navegador)
    driver.set_page_load_timeout(300)
    driver.set_script_timeout(300)
    # Vamos a mapear las opciones del usuario con el texto del CORDE
    RESULT_MAP = {'concord':'Concordancias',
                  'doc':'Documentos',
                  'par':'Párrafos',
                  'agrup':'Agrupaciones'}
    scrap_type = RESULT_MAP.get(args.type, None)
    # Double-check
    if scrap_type is None:
        raise ValueError('Opción no reconocida para el tipo de documentos')
    # Iniciamos la url del corde
    url = 'https://corpus.rae.es/cordenet.html'
    driver.get(url=url)
    
    # Esperamos como máximo 5 minutos hasta que se muestre la página de
    # obtención de resultados
    try:
        _ = WebDriverWait(driver, 300, ignored_exceptions=[StaleElementReferenceException]).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "td.submenu1")
            )
        )
    except Exception as e:
        print('no encontramos nada y ha habido una excepción', e)
        logging.error("No se mostraron resultados en el tiempo esperado")
        
    # Ahora que ha cargado la página el usuario configura su búsqueda
    # desde el nabegador. Nosotros extraemos el boton que el usuario
    # utilizará para comenzar la búsqueda
    submit_btn = driver.find_element(By.CSS_SELECTOR, "input[type='submit'][value='Recuperar']")

    logging.info('Esperando a que el usuario haga click en el botón <<Recuperar>>')

    # Esperamos a que el botón desaparezca es decir, que ya no exista 
    # como resultado de enviar la petición
    WebDriverWait(driver, 300).until(EC.staleness_of(submit_btn))
    
    logging.info('Analizando los resultados obtenidos en cada página')
    resultados = extraer_concordancias(driver)
    guardar_resultados(resultados,args.format,args.output)
    logging.info('Resultados guardados de forma exitosa.')
    driver.quit()

if __name__ == "__main__":
    main()


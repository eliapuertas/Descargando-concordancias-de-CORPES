from corde_scrapper import configurar_driver, extraer_concordancias, guardar_resultados
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException
import logging

navegador = 'firefox'
driver = configurar_driver(navegador)
driver.set_page_load_timeout(300)
driver.set_script_timeout(300)
# Vamos a mapear las opciones del usuario con el texto del CORDE
scrap_type = 'Concordancias'
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

print('esperando resultadoss...')
resultados = extraer_concordancias(driver)
print('Tenemos los resultados...')
guardar_resultados(resultados)
driver.quit()
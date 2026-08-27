from groq import AsyncGroq
from src.config import GROQ_API_KEY
from src.database import ConfiguracionDB, SessionLocal

#inicializar el cliente oficial de Groq
client = AsyncGroq(api_key=GROQ_API_KEY)

CLAVE_SYSTEM_PROMPT = "system_prompt"

# Valor por defecto: se usa mientras nadie lo edite desde el panel de
# administración (/admin/asistente.html -> src/routers/configuracion.py).
# No hace falta un deploy nuevo para cambiar el tono/catálogo del
# asistente — antes sí hacía falta, esto era deuda técnica documentada.
SYSTEM_PROMPT_POR_DEFECTO = """
Eres el asistente virtual oficial de "Agroindustria Guache, C.A.", una fábrica y planta agroindustrial fundada en 1998 ubicada en la Zona Industrial de Acarigua, Estado Portuguesa, Venezuela.

TU ROL Y OBJETIVO:
Atender a distribuidores, agroproductores e industrias. Tu trabajo es ofrecer información sobre nuestros productos a granel o empacados, explicar los servicios de planta y orientar al cliente para realizar cotizaciones al mayor.

INFORMACIÓN DE LA PLANTA:
- Ubicación: Zona Industrial, Acarigua, Estado Portuguesa, Venezuela.
- Capacidad: 12.000 toneladas/mes de procesamiento y 40.000 toneladas de almacenamiento en silos.
- Horario de atención: Lunes a Viernes de 7:00 a.m. a 5:00 p.m. (Recepción 24/7 en época de cosecha).
- Contacto de ventas: ventas@agroguache.com.ve.

SERVICIOS DE PLANTA DISPONIBLES:
1. Maquila y molienda (molienda, pulido y mezclado de granos con marca propia o a granel).
2. Secado y acondicionamiento (limpieza y clasificación de cosecha).
3. Almacenamiento en silos (control estricto de humedad y temperatura).
4. Control de calidad (análisis de humedad, impurezas y proteína lote por lote).
5. Distribución y transporte (flota propia para despacho regional puerta a puerta).
6. Asesoría agronómica (manejo de cultivo, poscosecha y nutrición animal).

CATÁLOGO DE PRODUCTOS (LÍNEAS Y SKUs):
1. HARINAS Y CEREALES:
   - Harina de maíz precocida (Presentaciones: 1 KG, 20 KG, 50 KG | SKU: HM-050)
   - Harina de trigo panadera (Presentaciones: 1 KG, 45 KG | SKU: HT-045)
   - Arroz pulido tipo I (Presentaciones: 1 KG, 50 KG | SKU: AR-050)
   - Sémola de maíz / Polenta (Presentaciones: 25 KG | SKU: SM-025)

2. ACEITES Y GRASAS:
   - Aceite vegetal comestible refinado (Presentaciones: 1 L, 18 L | SKU: AV-018)
   - Manteca vegetal para panadería (Presentaciones: 14 KG | SKU: MV-014)

3. NUTRICIÓN ANIMAL (ALIMENTO BALANCEADO):
   - Alimento para aves / engorde (Presentaciones: 40 KG | SKU: AE-040)
   - Alimento para ponedoras (Presentaciones: 40 KG | SKU: AP-040)
   - Alimento para cerdos / ceba (Presentaciones: 40 KG | SKU: AC-040)
   - Concentrado bovino / leche y carne (Presentaciones: 40 KG | SKU: CB-040)

4. AGROINSUMOS:
   - Semilla certificada de maíz híbrido (Presentaciones: 20 KG | SKU: SC-020)
   - Fertilizante granulado NPK (Presentaciones: 50 KG | SKU: FE-050)

5. SUBPRODUCTOS:
   - Afrecho de trigo (Presentaciones: 40 KG | SKU: AF-040)
   - Torta de soya (Presentaciones: 40 KG | SKU: TS-040)

REGLAS DE RESPUESTA:
- Tono: Profesional, atento, experto en el agro venezolano, amigable y eficiente.
- Si el cliente pregunta por PRECIOS ESPECÍFICOS: Explícale amablemente que las cotizaciones dependen del volumen del pedido y el destino del despacho. Pídele que te indique qué cantidad necesita y la presentación de su interés para canalizar la orden con el departamento de ventas.
- Destaca siempre la calidad del producto, el respaldo de contar con planta propia en Acarigua y el código SKU de la presentación cuando refieras un producto.
- Mantén las respuestas claras y estructuradas (usa viñetas o negrillas cuando muestres opciones).
"""


def obtener_system_prompt() -> str:
    """
    Devuelve el prompt configurado desde el panel si existe y no está
    vacío; si no, el valor por defecto. Sesión propia y de corta vida
    (no depende de FastAPI Depends) porque también la usa el bot de
    Telegram, que corre fuera de una request HTTP.
    """
    db = SessionLocal()
    try:
        fila = db.query(ConfiguracionDB).filter(ConfiguracionDB.clave == CLAVE_SYSTEM_PROMPT).first()
        if fila and fila.valor.strip():
            return fila.valor
        return SYSTEM_PROMPT_POR_DEFECTO
    finally:
        db.close()


async def generar_respuesta_llm(prompt_usuario: str) -> str:
    """
    Envía el mensaje del usuario a Groq y devuelve el texto generado.
    """
    try:
        response = await client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[
                {
                    "role": "system",
                    "content": obtener_system_prompt(),
                },
                {
                    "role": "user",
                    "content": prompt_usuario,
                }
            ],
            temperature=0.5
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"⚠️ Error en la API de Groq: {e}")
        return "Disculpa, en estos momentos, hay una revolución de manadas Guache, intenta comunicarte más tarde."
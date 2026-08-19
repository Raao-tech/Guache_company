#!/usr/bin/env python3
"""
Migra a la base de datos los 4 artículos de ejemplo que antes vivían como
archivos HTML estáticos en web/blog/ (uno por tipo de cliente de
EMPRESA.md §8). Es idempotente: si un slug ya existe, no lo duplica.

Uso:
    venv/bin/python deploy/seed_blog.py
"""
import sys
from datetime import datetime
from pathlib import Path

# Permite correr el script como `python deploy/seed_blog.py` desde
# cualquier directorio, agregando la raíz del proyecto a sys.path.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.database import Base, BlogPostDB, SessionLocal, engine

POSTS = [
    {
        "slug": "comenzar-en-agricultura",
        "titulo": "Primeros pasos para el pequeño agricultor: cómo trabajar con una agroindustria puede cambiar tu cosecha",
        "resumen": "Cómo el almacenamiento, la asesoría técnica y la maquinaria pueden cambiar el resultado de tu cosecha.",
        "audiencia": "Para agricultores",
        "contenido": """Si trabajás la tierra en Portuguesa, Barinas o cualquiera de los estados donde el llano venezolano se extiende, seguramente ya sabés que el trabajo no termina cuando se levanta la cosecha. Lo que pase después —dónde se guarda, cómo se maneja, a quién se le vende— define buena parte del resultado del año. Este artículo es una guía sencilla de lo que un pequeño o mediano agricultor debería tener en cuenta al empezar a trabajar con una agroindustria como Guache.

## 1. El almacenamiento no es un detalle menor

Uno de los errores más comunes es subestimar el impacto de un mal almacenamiento. La humedad y la temperatura descontroladas pueden arruinar en semanas lo que costó meses producir. Por eso Guache ofrece almacenamiento en silos propios, con control de humedad y temperatura, para productores que todavía no cuentan con capacidad de acopio propia. No hace falta tener una bodega para proteger tu cosecha.

## 2. Asesoría técnica, desde la semilla hasta la poscosecha

El acompañamiento técnico no debería empezar cuando algo sale mal, sino desde antes de sembrar. Guache ofrece asesoramiento en selección de semilla, manejo de tierra y cría, pensado para acompañar todo el ciclo — no solo la venta final.

- Selección de semilla adecuada para tu zona y tipo de suelo.
- Manejo de cultivo durante las distintas etapas de crecimiento.
- Buenas prácticas de manejo poscosecha, para llegar en mejores condiciones al acopio.

## 3. Acceso a maquinaria, sin tener que comprarla de entrada

La inversión en maquinaria agrícola suele ser una de las barreras más grandes para un productor que está creciendo. Guache facilita el acceso a equipos para siembra, cosecha y manejo pecuario, para que la falta de maquinaria propia no sea lo que frene la producción.

## 4. Vender tu cosecha, no solo comprar insumos

La relación con Guache no es de una sola vía. Muchos agricultores y cooperativas que utilizan los servicios de almacenamiento y asesoría también venden su cosecha directamente a la empresa — construyendo, con el tiempo, una relación comercial de largo plazo en vez de transacciones puntuales.

## Cómo dar el primer paso

Si estás por decidir dónde almacenar tu próxima cosecha, o simplemente querés entender mejor qué servicios existen para productores como vos, lo más directo es escribirle a Guache o pedir una cotización.""",
    },
    {
        "slug": "alimento-balanceado-guia",
        "titulo": "Cómo elegir el alimento balanceado correcto según tu tipo de producción",
        "resumen": "Bovino, avícola o truchicultura: qué considerar según tu etapa de producción.",
        "audiencia": "Para productores pecuarios",
        "contenido": """No existe un único "alimento balanceado" que sirva para todos los productores pecuarios. Un ganadero de leche, un avicultor de engorde y un truchicultor tienen necesidades nutricionales completamente distintas, y elegir mal puede significar meses de resultados por debajo de lo esperado. Guache formula alimento balanceado para tres sectores pecuarios — bovino, avícola y truchicultura — y esto es lo que conviene tener claro antes de elegir.

## Sector bovino: leche y carne no son lo mismo

Un concentrado pensado para ganado de leche prioriza energía y proteína disponible para sostener la producción láctea, mientras que uno para ganado de carne se enfoca en ganancia de peso. Usar la misma fórmula para ambos objetivos rara vez da el mejor resultado. Lo primero es tener claro cuál es el objetivo productivo del hato antes de elegir el concentrado.

## Sector avícola: engorde vs. ponedoras

Igual que en bovinos, un ave de engorde y una gallina ponedora tienen requerimientos distintos: la primera necesita ganancia de peso rápida y eficiente, la segunda necesita sostener la postura de forma constante en el tiempo. Guache formula alimento diferenciado para ambos casos.

## Truchicultura: una línea distinta, para zonas altas

La producción de trucha es una línea diferenciadora dentro de la oferta de Guache, orientada a productores de acuicultura en zonas altas como Mérida. Es un sector con necesidades muy específicas de formulación, y contar con un proveedor que ya tenga experiencia en esta línea particular hace diferencia frente a adaptar un alimento genérico.

## Lo que deberías preguntarle siempre a tu proveedor

- ¿La fórmula está pensada específicamente para mi etapa de producción (engorde, ponedoras, leche, carne)?
- ¿Hay control de calidad por lote (humedad, impurezas, proteína)?
- ¿Puede sostener el volumen que necesito de forma consistente, mes a mes?

Guache produce su alimento balanceado en la misma planta de Acarigua donde procesa sus rubros agrícolas, con control de calidad lote por lote — lo que permite trazabilidad desde el grano hasta el saco de 40 KG que llega a tu unidad de producción.""",
    },
    {
        "slug": "elegir-proveedor-mayorista",
        "titulo": "5 cosas a evaluar al elegir un proveedor mayorista de harinas y cereales",
        "resumen": "Consistencia, trazabilidad y logística: lo que debería ofrecerte tu proveedor de harinas y cereales.",
        "audiencia": "Para distribuidores",
        "contenido": """Para un distribuidor o mayorista, el proveedor no es solo quien vende el producto — es quien determina si vas a poder cumplirle a tus propios clientes mes tras mes. Estas son cinco cosas que vale la pena evaluar antes de comprometerte con un proveedor de harinas, cereales o aceites en presentaciones industriales.

## 1. Consistencia del producto, lote a lote

Un producto que varía de calidad entre un pedido y otro genera reclamos que terminan cayendo sobre vos, no sobre el proveedor. Preguntá si existe control de calidad por lote — análisis de humedad, impurezas y proteína — antes de que el producto salga de planta.

## 2. Capacidad real de producción

Un proveedor pequeño puede tener buen producto, pero no siempre puede sostener volumen en tus momentos de mayor demanda. Guache procesa hasta 12.000 toneladas al mes y almacena hasta 40.000 toneladas en silos propios, lo que da margen para sostener pedidos recurrentes sin depender de terceros.

## 3. Logística y distribución

La cercanía territorial importa: un proveedor que opera cerca de tu zona de distribución reduce tiempos y costos de despacho. Guache tiene presencia comercial en siete estados de Venezuela — Portuguesa, Mérida, Barinas, Zulia, Lara, Guárico y Cojedes — lo que cubre gran parte del eje agrícola occidental y central del país.

## 4. Variedad de presentaciones industriales

No todos los distribuidores necesitan el mismo formato. Contar con un proveedor que ofrezca distintas presentaciones (sacos de 20, 45 o 50 KG, bultos de 1 KG, aceite en presentaciones de 18 L) da flexibilidad para atender distintos segmentos de tu propia red de clientes.

## 5. Una relación de largo plazo, no una transacción puntual

El modelo de negocio más sólido para un distribuidor no es cambiar de proveedor cada vez que aparece un precio más bajo, sino construir una relación de confianza donde el cumplimiento de acuerdos comerciales y la transparencia en cotizaciones sean la norma. Eso es lo que Guache busca sostener con sus distribuidores desde hace más de 25 años.""",
    },
    {
        "slug": "recetas-harina-de-maiz",
        "titulo": "3 recetas tradicionales latinoamericanas con harina de maíz",
        "resumen": "Un adelanto del sabor latinoamericano que Guache quiere llevar a más hogares en España y Colombia.",
        "audiencia": "Para tu hogar",
        "contenido": """Parte de lo que Guache quiere llevar a España y Colombia no son solo productos, sino la tradición que hay detrás de ellos. La harina de maíz precocida es, para muchos hogares venezolanos, el punto de partida de la comida de todos los días. Estas tres recetas son simples, rinden bien y son un buen punto de partida si querés conocer ese sabor desde tu propia cocina — mientras seguimos preparando la llegada de nuestras presentaciones al detal.

## 1. Arepas clásicas

La base de todo. Se mezcla harina de maíz precocida con agua tibia y una pizca de sal hasta formar una masa suave que no se pegue en las manos. Se forman bolas, se aplanan en discos de un par de centímetros de grosor, y se cocinan en un budare o sartén caliente hasta dorar por ambos lados — después se terminan de cocinar unos minutos al horno si querés que queden bien esponjosas por dentro. Se rellenan con lo que tengas a mano: queso, aguacate, caraotas.

## 2. Cachapas dulces

Aunque la cachapa tradicional se hace con maíz tierno, una versión rápida y sabrosa se prepara con harina de maíz precocida, un poco de leche, huevo, azúcar y una pizca de sal, hasta lograr una mezcla más líquida que la de las arepas. Se cocina en budare o sartén como si fuera un panqueque, y se sirve con queso fresco o mantequilla — el contraste dulce-salado es el gran secreto de esta receta.

## 3. Buñuelos de maíz

Para un postre sencillo: se mezcla harina de maíz precocida con un poco de harina de trigo, azúcar, huevo y leche hasta formar una masa espesa. Se forman bolitas pequeñas y se fríen en aceite caliente hasta dorar. Se sirven calientes, espolvoreados con azúcar o bañados en un almíbar simple de papelón o panela.

## Un sabor que viaja

Estas recetas son parte de la identidad que Guache quiere mantener como sello de marca también fuera de Venezuela — el orgullo por el origen y la tradición agrícola latinoamericana. Todavía no tenemos tienda en línea activa para comprar directamente al detal, pero ya estamos preparando esa etapa.""",
    },
]


def main() -> None:
    Base.metadata.create_all(bind=engine)  # no-op si las tablas ya existen (las crea alembic)
    db = SessionLocal()
    try:
        creados = 0
        for post in POSTS:
            existe = db.query(BlogPostDB).filter(BlogPostDB.slug == post["slug"]).first()
            if existe:
                continue
            db.add(BlogPostDB(**post, publicado=True, fecha_publicacion=datetime.now()))
            creados += 1
        db.commit()
        print(f"Listo: {creados} artículo(s) nuevo(s) creado(s) (de {len(POSTS)} en total).")
    finally:
        db.close()


if __name__ == "__main__":
    main()

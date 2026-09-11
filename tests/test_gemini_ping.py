# test_gemini_ping.py
import sys
from google import genai
from google.genai import types

def run_sanity_check():
    # Tu clave API directa para Google AI Studio
    API_KEY = "AQ.Ab8RN6ICVy4AzeVQyTdeLMv2Zma-iIkIEFdi0MSoahGW0ycEpw"
    
    print("=======================================================================")
    print("🛰️  Iniciando Ping Directo hacia los servidores de Google AI Studio...")
    print("📋 Probando modelo de alta eficiencia: gemini-3.5-flash-lite")
    print("=======================================================================")
    
    try:
        # Inicialización del cliente oficial moderno de Google
        client = genai.Client(api_key=API_KEY)
        
        # Inferencia con la versión optimizada para alta velocidad y cuota extendida
        response = client.models.generate_content(
            model="gemini-3.5-flash-lite",
            contents="Hola, responde únicamente con la palabra 'CONECTADO'.",
            config=types.GenerateContentConfig(temperature=0.1)
        )
        
        print("\n🎉 ¡ÉXITO ROTUNDO DE INFERENCIA EN LA NUBE!")
        print(f"🤖 Respuesta de Gemini 3.5 Flash-Lite: {response.text.strip()}")
        print("=======================================================================")
        print("✅ Diagnóstico: Tu entorno está listo y optimizado para la cuota gratuita.")
        print("=======================================================================")
        
    except Exception as err:
        print("\n🚨 CORTOCUITO EXTRÍNSECO DETECTADO:")
        print(f"❌ Detalle del Error de Google: {err}")
        print("=======================================================================")
        print("❌ Diagnóstico: La solicitud falló.")
        print("📌 Puntos a revisar:")
        print("   1. Confirma que tu IP/región no tenga restricciones de geolocalización.")
        print("   2. Asegúrate de no haber activado la facturación en este proyecto (mantenlo en gratis).")
        print("=======================================================================")

if __name__ == "__main__":
    run_sanity_check()

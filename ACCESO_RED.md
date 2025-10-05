# 🌐 Acceso en Red - Exoplanet Classifier API

## ✅ **Configuración Completada**

El backend está configurado para ser accesible desde cualquier computadora en la misma red local.

---

## 📡 **Información de Conexión**

### **IP del Servidor:**
```
10.231.220.205
```

### **Puerto:**
```
8000
```

### **URLs de Acceso:**
- **API Base**: `http://10.231.220.205:8000`
- **Swagger UI**: `http://10.231.220.205:8000/docs`
- **ReDoc**: `http://10.231.220.205:8000/redoc`
- **OpenAPI Schema**: `http://10.231.220.205:8000/openapi.json`

---

## 🖥️ **Instrucciones para Acceso desde Otra Computadora**

### **1. Verificar Conectividad de Red**
- Asegúrate de que ambas computadoras estén en la **misma red local**
- Pueden estar conectadas al mismo router WiFi o red cableada

### **2. Acceso desde Navegador Web**
Abre tu navegador y visita:
```
http://10.231.220.205:8000/docs
```

### **3. Acceso desde Aplicaciones/Postman**
Usa la URL base para hacer requests:
```
http://10.231.220.205:8000
```

---

## 🧪 **Pruebas de Conectividad**

### **Desde la Computadora Cliente:**

#### **1. Verificar Conectividad Básica**
```bash
ping 10.231.220.205
```

#### **2. Probar Acceso a la API**
```bash
curl http://10.231.220.205:8000/model/info
```

#### **3. Probar Swagger UI**
Abre en el navegador:
```
http://10.231.220.205:8000/docs
```

---

## 🔧 **Endpoints Disponibles para Pruebas**

### **Información del Sistema**
```bash
GET http://10.231.220.205:8000/model/info
```

### **Versiones de Modelos**
```bash
GET http://10.231.220.205:8000/model-versions/hgb_exoplanet_model
```

### **Predicción Individual**
```bash
POST http://10.231.220.205:8000/predict
Content-Type: application/json

{
  "data": [
    {
      "koi_period": 10.5,
      "koi_duration": 2.1,
      "koi_depth": 0.001,
      "koi_prad": 1.2,
      "koi_steff": 5778,
      "koi_slogg": 4.4
    }
  ]
}
```

### **Información Detallada de Modelo**
```bash
GET http://10.231.220.205:8000/model-info/hgb_exoplanet_model/v1.0.2
```

---

## 🛡️ **Consideraciones de Seguridad**

### **⚠️ Acceso Público**
- El servidor está configurado para **acceso público en la red local**
- Cualquier dispositivo en la misma red puede acceder a la API
- **No recomendado para producción** sin autenticación adicional

### **🔒 Para Producción**
Si necesitas mayor seguridad, considera:
- Implementar autenticación JWT
- Usar HTTPS con certificados SSL
- Configurar firewall para restringir acceso
- Usar variables de entorno para configuración

---

## 🚨 **Solución de Problemas**

### **Error: "Connection Refused"**
1. Verifica que el servidor esté ejecutándose:
   ```bash
   # En la computadora servidor
   lsof -i :8000
   ```

2. Verifica la IP del servidor:
   ```bash
   # En la computadora servidor
   ifconfig | grep "inet "
   ```

### **Error: "Timeout"**
1. Verifica que ambas computadoras estén en la misma red
2. Verifica que no haya firewall bloqueando el puerto 8000
3. Prueba con `ping` para verificar conectividad básica

### **Error: "Page Not Found"**
1. Verifica que la URL sea correcta: `http://10.231.220.205:8000/docs`
2. Asegúrate de que el servidor esté completamente iniciado

---

## 📱 **Acceso desde Diferentes Dispositivos**

### **Computadora Windows/Mac/Linux**
- Usa cualquier navegador web
- Accede a: `http://10.231.220.205:8000/docs`

### **Móvil/Tablet**
- Conecta a la misma red WiFi
- Abre navegador y ve a: `http://10.231.220.205:8000/docs`

### **Postman/Insomnia**
- Crea nueva request
- URL: `http://10.231.220.205:8000/model/info`
- Método: GET

---

## 🎯 **Estado Actual**

- ✅ **Servidor ejecutándose** en puerto 8000
- ✅ **Acceso en red habilitado** (host: 0.0.0.0)
- ✅ **API funcionando** correctamente
- ✅ **Swagger UI accesible** desde red local
- ✅ **Todos los endpoints** disponibles

---

## 📞 **Información de Contacto**

Si necesitas cambiar la IP o configuración:
1. Ejecuta `ifconfig` para obtener la IP actual
2. Actualiza este archivo con la nueva IP
3. Reinicia el servidor con `python3 run.py`

---

*Configuración realizada el: $(date)*
*IP del servidor: 10.231.220.205*
*Puerto: 8000*
*Estado: FUNCIONANDO* ✅

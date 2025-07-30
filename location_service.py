"""
location_service.py - Servicio de validación de ubicación GPS para HISPE PULSE
Valida que el usuario esté dentro del rango permitido para marcar asistencia
"""

import math
import logging
import re
import os
from typing import Dict, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

class LocationValidationError(Exception):
    """Excepción personalizada para errores de validación de ubicación"""
    pass

class LocationService:
    def __init__(self):
        # Configuración de tolerancia (700 metros según tu .env)
        self.ALLOWED_DISTANCE_METERS = float(os.getenv('MAX_GPS_DISTANCE', '700.0'))
        
        # Radio de la Tierra en metros
        self.EARTH_RADIUS_METERS = 6371000
        
        # Patrones para extraer coordenadas del QR
        self.QR_PATTERNS = [
            # Formato: empresa|area|codigo|lat,lng|establecimiento|...
            r'^[^|]*\|[^|]*\|[^|]*\|(-?\d+\.?\d*),\s*(-?\d+\.?\d*)\|',
            # Formato alternativo: lat,lng al inicio
            r'^(-?\d+\.?\d*),\s*(-?\d+\.?\d*)\|',
            # Formato JSON: {"lat": x, "lng": y}
            r'"lat"\s*:\s*(-?\d+\.?\d*)[^}]*"lng"\s*:\s*(-?\d+\.?\d*)',
            # Formato simple: lat,lng
            r'^(-?\d+\.?\d*),\s*(-?\d+\.?\d*)$'
        ]

    def validate_coordinates(self, latitude: float, longitude: float) -> bool:
        """
        Validar que las coordenadas estén en rangos válidos
        
        Args:
            latitude: Latitud (-90 a 90)
            longitude: Longitud (-180 a 180)
            
        Returns:
            bool: True si las coordenadas son válidas
        """
        try:
            lat = float(latitude)
            lng = float(longitude)
            
            if not (-90 <= lat <= 90):
                raise LocationValidationError(f"Latitud fuera de rango: {lat}")
            
            if not (-180 <= lng <= 180):
                raise LocationValidationError(f"Longitud fuera de rango: {lng}")
                
            return True
            
        except (ValueError, TypeError) as e:
            raise LocationValidationError(f"Coordenadas inválidas: {e}")

    def extract_qr_coordinates(self, qr_code: str) -> Optional[Tuple[float, float]]:
        """
        Extraer coordenadas GPS del código QR
        
        Args:
            qr_code: Contenido del código QR
            
        Returns:
            Tuple[float, float]: (latitud, longitud) o None si no se encuentra
        """
        if not qr_code or not qr_code.strip():
            return None
            
        qr_clean = qr_code.strip()
        
        # Intentar cada patrón
        for pattern in self.QR_PATTERNS:
            match = re.search(pattern, qr_clean)
            if match:
                try:
                    lat = float(match.group(1))
                    lng = float(match.group(2))
                    
                    # Validar coordenadas
                    if self.validate_coordinates(lat, lng):
                        logger.info(f"🎯 Coordenadas extraídas del QR: {lat}, {lng}")
                        return (lat, lng)
                        
                except (ValueError, LocationValidationError) as e:
                    logger.warning(f"⚠️ Coordenadas inválidas en QR: {e}")
                    continue
        
        logger.warning(f"❌ No se pudieron extraer coordenadas del QR: {qr_clean[:50]}...")
        return None

    def calculate_distance(self, lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """
        Calcular distancia entre dos puntos usando la fórmula de Haversine
        
        Args:
            lat1, lng1: Coordenadas del primer punto
            lat2, lng2: Coordenadas del segundo punto
            
        Returns:
            float: Distancia en metros
        """
        try:
            # Convertir grados a radianes
            lat1_rad = math.radians(lat1)
            lng1_rad = math.radians(lng1)
            lat2_rad = math.radians(lat2)
            lng2_rad = math.radians(lng2)
            
            # Diferencias
            dlat = lat2_rad - lat1_rad
            dlng = lng2_rad - lng1_rad
            
            # Fórmula de Haversine
            a = (math.sin(dlat / 2) ** 2 + 
                 math.cos(lat1_rad) * math.cos(lat2_rad) * 
                 math.sin(dlng / 2) ** 2)
            
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
            
            # Distancia en metros
            distance = self.EARTH_RADIUS_METERS * c
            
            logger.debug(f"📏 Distancia calculada: {distance:.2f}m")
            return distance
            
        except Exception as e:
            logger.error(f"❌ Error calculando distancia: {e}")
            raise LocationValidationError(f"Error en cálculo de distancia: {e}")

    def validate_location(
        self, 
        user_lat: float, 
        user_lng: float, 
        qr_code: str,
        tolerance_meters: Optional[float] = None
    ) -> Dict[str, any]:
        """
        Validar si el usuario está en ubicación permitida
        
        Args:
            user_lat: Latitud del usuario
            user_lng: Longitud del usuario
            qr_code: Código QR con coordenadas del punto de marcación
            tolerance_meters: Tolerancia en metros (opcional)
            
        Returns:
            Dict con resultado de validación:
            {
                'valid': bool,
                'distance': float,
                'message': str,
                'qr_coordinates': tuple,
                'user_coordinates': tuple
            }
        """
        tolerance = tolerance_meters or self.ALLOWED_DISTANCE_METERS
        
        try:
            # Validar coordenadas del usuario
            self.validate_coordinates(user_lat, user_lng)
            
            # Extraer coordenadas del QR
            qr_coords = self.extract_qr_coordinates(qr_code)
            if not qr_coords:
                return {
                    'valid': False,
                    'distance': None,
                    'message': 'El código QR no contiene coordenadas válidas de ubicación',
                    'qr_coordinates': None,
                    'user_coordinates': (user_lat, user_lng),
                    'error_code': 'INVALID_QR_COORDINATES'
                }
            
            qr_lat, qr_lng = qr_coords
            
            # Calcular distancia
            distance = self.calculate_distance(user_lat, user_lng, qr_lat, qr_lng)
            
            # Verificar si está dentro del rango
            is_valid = distance <= tolerance
            
            if is_valid:
                message = f'✅ Ubicación válida (distancia: {distance:.1f}m)'
                logger.info(f"✅ Validación GPS exitosa - Distancia: {distance:.1f}m <= {tolerance}m")
            else:
                message = f'❌ Muy lejos del punto de marcación. Distancia: {distance:.1f}m (máximo: {tolerance}m)'
                logger.warning(f"❌ Validación GPS falló - Distancia: {distance:.1f}m > {tolerance}m")
            
            return {
                'valid': is_valid,
                'distance': round(distance, 1),
                'message': message,
                'qr_coordinates': qr_coords,
                'user_coordinates': (user_lat, user_lng),
                'tolerance': tolerance,
                'error_code': None if is_valid else 'DISTANCE_EXCEEDED'
            }
            
        except LocationValidationError as e:
            logger.error(f"❌ Error de validación: {e}")
            return {
                'valid': False,
                'distance': None,
                'message': f'Error de validación: {str(e)}',
                'qr_coordinates': qr_coords if 'qr_coords' in locals() else None,
                'user_coordinates': (user_lat, user_lng),
                'error_code': 'VALIDATION_ERROR'
            }
            
        except Exception as e:
            logger.error(f"❌ Error inesperado en validación: {e}")
            return {
                'valid': False,
                'distance': None,
                'message': 'Error interno procesando ubicación',
                'qr_coordinates': None,
                'user_coordinates': (user_lat, user_lng),
                'error_code': 'INTERNAL_ERROR'
            }

    def validate_qr_format(self, qr_code: str) -> Dict[str, any]:
        """
        Validar formato del código QR y extraer información
        
        Args:
            qr_code: Contenido del código QR
            
        Returns:
            Dict con información del QR:
            {
                'valid': bool,
                'coordinates': tuple,
                'company': str,
                'area': str,
                'establishment_id': str,
                'message': str
            }
        """
        try:
            if not qr_code or not qr_code.strip():
                return {
                    'valid': False,
                    'message': 'Código QR vacío',
                    'error_code': 'EMPTY_QR'
                }
            
            qr_clean = qr_code.strip()
            
            # Intentar formato estándar: empresa|area|codigo|lat,lng|establecimiento|...
            parts = qr_clean.split('|')
            if len(parts) >= 5:
                try:
                    company = parts[0].strip()
                    area = parts[1].strip()
                    code = parts[2].strip()
                    coords_str = parts[3].strip()
                    establishment = parts[4].strip()
                    
                    # Extraer coordenadas
                    coords = self.extract_qr_coordinates(qr_code)
                    if coords:
                        return {
                            'valid': True,
                            'coordinates': coords,
                            'company': company,
                            'area': area,
                            'code': code,
                            'establishment_id': establishment,
                            'message': 'QR válido con formato estándar',
                            'format': 'standard'
                        }
                        
                except Exception as e:
                    logger.warning(f"Error parseando QR estándar: {e}")
            
            # Intentar extraer solo coordenadas
            coords = self.extract_qr_coordinates(qr_code)
            if coords:
                return {
                    'valid': True,
                    'coordinates': coords,
                    'company': 'No especificado',
                    'area': 'No especificado',
                    'code': qr_clean[:20],
                    'establishment_id': 'No especificado',
                    'message': 'QR válido con coordenadas',
                    'format': 'coordinates_only'
                }
            
            return {
                'valid': False,
                'message': 'Formato de QR no reconocido o sin coordenadas válidas',
                'error_code': 'INVALID_FORMAT'
            }
            
        except Exception as e:
            logger.error(f"Error validando formato QR: {e}")
            return {
                'valid': False,
                'message': f'Error procesando QR: {str(e)}',
                'error_code': 'PROCESSING_ERROR'
            }

    def get_location_info(self, latitude: float, longitude: float) -> Dict[str, str]:
        """
        Obtener información descriptiva de una ubicación
        
        Args:
            latitude: Latitud
            longitude: Longitud
            
        Returns:
            Dict con información de la ubicación
        """
        try:
            # Información básica de coordenadas
            lat_hemisphere = "Norte" if latitude >= 0 else "Sur"
            lng_hemisphere = "Este" if longitude >= 0 else "Oeste"
            
            # Formatear coordenadas
            lat_formatted = f"{abs(latitude):.6f}° {lat_hemisphere}"
            lng_formatted = f"{abs(longitude):.6f}° {lng_hemisphere}"
            
            return {
                'latitude_formatted': lat_formatted,
                'longitude_formatted': lng_formatted,
                'coordinates_string': f"{latitude:.6f}, {longitude:.6f}",
                'hemisphere': f"{lat_hemisphere}-{lng_hemisphere}",
                'precision': '±3-5 metros (GPS típico)'
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo info de ubicación: {e}")
            return {
                'latitude_formatted': 'Error',
                'longitude_formatted': 'Error',
                'coordinates_string': 'Error',
                'hemisphere': 'Desconocido',
                'precision': 'No disponible'
            }

    def is_within_peru(self, latitude: float, longitude: float) -> bool:
        """
        Verificar si las coordenadas están dentro del territorio peruano (aproximado)
        
        Args:
            latitude: Latitud
            longitude: Longitud
            
        Returns:
            bool: True si está dentro de Perú
        """
        try:
            # Límites aproximados de Perú
            peru_bounds = {
                'north': 0.5,
                'south': -18.5,
                'east': -68.0,
                'west': -81.5
            }
            
            is_within = (peru_bounds['south'] <= latitude <= peru_bounds['north'] and
                        peru_bounds['west'] <= longitude <= peru_bounds['east'])
            
            if not is_within:
                logger.warning(f"⚠️ Coordenadas fuera de Perú: {latitude}, {longitude}")
            
            return is_within
            
        except Exception as e:
            logger.error(f"Error verificando ubicación en Perú: {e}")
            return True  # Asumir válido en caso de error

    def validate_accuracy(self, accuracy: Optional[float]) -> Dict[str, any]:
        """
        Validar la precisión del GPS
        
        Args:
            accuracy: Precisión en metros (opcional)
            
        Returns:
            Dict con validación de precisión
        """
        try:
            max_accuracy = float(os.getenv('MAX_GPS_ACCURACY', '600.0'))
            
            if accuracy is None:
                return {
                    'valid': True,
                    'message': 'Precisión no reportada',
                    'quality': 'unknown'
                }
            
            if accuracy <= 5:
                return {
                    'valid': True,
                    'message': f'Excelente precisión GPS: ±{accuracy}m',
                    'quality': 'excellent'
                }
            elif accuracy <= 20:
                return {
                    'valid': True,
                    'message': f'Buena precisión GPS: ±{accuracy}m',
                    'quality': 'good'
                }
            elif accuracy <= max_accuracy:
                return {
                    'valid': True,
                    'message': f'Precisión GPS aceptable: ±{accuracy}m',
                    'quality': 'acceptable'
                }
            else:
                return {
                    'valid': False,
                    'message': f'Precisión GPS insuficiente: ±{accuracy}m (requiere <{max_accuracy}m)',
                    'quality': 'poor'
                }
                
        except Exception as e:
            logger.error(f"Error validando precisión GPS: {e}")
            return {
                'valid': True,
                'message': 'Error evaluando precisión',
                'quality': 'error'
            }

    def generate_location_report(
        self, 
        user_lat: float, 
        user_lng: float, 
        qr_code: str,
        accuracy: Optional[float] = None
    ) -> Dict[str, any]:
        """
        Generar reporte completo de validación de ubicación
        
        Args:
            user_lat: Latitud del usuario
            user_lng: Longitud del usuario
            qr_code: Código QR
            accuracy: Precisión GPS (opcional)
            
        Returns:
            Dict con reporte completo
        """
        try:
            # Validación principal
            validation = self.validate_location(user_lat, user_lng, qr_code)
            
            # Validación de QR
            qr_info = self.validate_qr_format(qr_code)
            
            # Información de ubicación
            user_info = self.get_location_info(user_lat, user_lng)
            qr_location_info = None
            if qr_info.get('coordinates'):
                qr_lat, qr_lng = qr_info['coordinates']
                qr_location_info = self.get_location_info(qr_lat, qr_lng)
            
            # Validación de precisión
            accuracy_info = self.validate_accuracy(accuracy)
            
            # Verificar si está en Perú
            in_peru = self.is_within_peru(user_lat, user_lng)
            
            return {
                'validation': validation,
                'qr_info': qr_info,
                'user_location': {
                    'coordinates': (user_lat, user_lng),
                    'info': user_info,
                    'in_peru': in_peru
                },
                'qr_location': {
                    'coordinates': qr_info.get('coordinates'),
                    'info': qr_location_info
                },
                'accuracy': accuracy_info,
                'timestamp': datetime.now().isoformat(),
                'summary': {
                    'overall_valid': (validation['valid'] and 
                                    qr_info['valid'] and 
                                    accuracy_info['valid'] and 
                                    in_peru),
                    'primary_issue': self._get_primary_issue(validation, qr_info, accuracy_info, in_peru)
                }
            }
            
        except Exception as e:
            logger.error(f"Error generando reporte de ubicación: {e}")
            return {
                'validation': {'valid': False, 'message': 'Error interno'},
                'summary': {
                    'overall_valid': False,
                    'primary_issue': f'Error interno: {str(e)}'
                }
            }

    def _get_primary_issue(self, validation, qr_info, accuracy_info, in_peru):
        """Obtener el problema principal si la validación falla"""
        if not qr_info['valid']:
            return qr_info.get('message', 'QR inválido')
        elif not in_peru:
            return 'Ubicación fuera del territorio peruano'
        elif not accuracy_info['valid']:
            return accuracy_info.get('message', 'Precisión GPS insuficiente')
        elif not validation['valid']:
            return validation.get('message', 'Fuera del rango permitido')
        else:
            return 'Validación exitosa'

# Instancia global del servicio
location_service = LocationService()
"""
meme_hunter.core.exceptions - Jerarquía Canónica de Excepciones del Dominio.
"""

class MemeHunterError(Exception):
    """Excepción base para todos los errores del ecosistema Meme Hunter."""
    pass


class ConfigurationError(MemeHunterError):
    """Error al cargar variables de entorno, configuración o claves críticas."""
    pass


class SecurityError(MemeHunterError):
    """Fallo en descifrado de bóveda, autenticación o violación de seguridad."""
    pass


class DatabaseError(MemeHunterError):
    """Error de concurrencia, bloqueo o transacción fallida en SQLite WAL."""
    pass


class DataFeedError(MemeHunterError):
    """Fallo en la ingesta de mercado, gap de datos o libro L2 corrupto."""
    pass


class ASTCompilationError(MemeHunterError):
    """Fórmula de alfa sintácticamente inválida o con código no permitido (Zero-Eval)."""
    pass


class ValidationGatingError(MemeHunterError):
    """Rechazo de factor por compuertas fuera de muestra (PBO, DSR, correlación)."""
    pass


class RiskGateError(MemeHunterError):
    """Rechazo de operación por compuertas de riesgo pre-trade o filtros institucionales."""
    pass


class KillSwitchActivatedError(RiskGateError):
    """Disparo del Kill Switch absoluto por superación de límite de drawdown global."""
    pass


class ExecutionError(MemeHunterError):
    """Fallo al enviar, confirmar o enrutar órdenes en Freqtrade o CCXT."""
    pass


class AgentExecutionError(MemeHunterError):
    """Fallo en la inferencia o ejecución de un nodo del DAG multi-agente."""
    pass

import random
import os
import itertools # Necesario para combinaciones de cartas
from flask import Flask, render_template, request, redirect, url_for, session

# --- Constantes del Juego ---
FICHAS_INICIALES = 1000
MIN_APUESTA = 10 # Apuesta mínima para apostar/subir

# --- Clase Carta ---
class Carta:
    """Representa una carta individual con su valor, palo, nombre y rango numérico."""
    def __init__(self, valor, palo):
        self.valor = valor
        self.palo = palo
        self.nombre = valor + palo
        self.valor_rank = self._get_valor_rank()
        self.palo_texto = self._get_palo_texto() # Para accesibilidad en HTML (ej. "Corazones")

    def __str__(self):
        """Representación de la carta (ej. 'A♠')."""
        return f"{self.valor}{self.palo}"

    def __repr__(self):
        """Representación para depuración."""
        return f"Carta('{self.valor}', '{self.palo}')"

    def _get_valor_rank(self):
        """Asigna un rango numérico a cada valor de carta para facilitar comparaciones."""
        if self.valor.isdigit():
            return int(self.valor)
        elif self.valor == 'J':
            return 11
        elif self.valor == 'Q':
            return 12
        elif self.valor == 'K':
            return 13
        elif self.valor == 'A':
            return 14 # El As es la carta más alta en póker (puede ser 1 para escaleras bajas)

    def _get_palo_texto(self):
        """Devuelve el nombre del palo en texto (para accesibilidad)."""
        if self.palo == '♠':
            return "Espadas"
        elif self.palo == '♥':
            return "Corazones"
        elif self.palo == '♦':
            return "Diamantes"
        elif self.palo == '♣':
            return "Tréboles"
        return ""

# --- Clase Baraja ---
class Baraja:
    """Representa una baraja estándar de 52 cartas y sus operaciones."""
    def __init__(self):
        self.valores = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
        self.palos = ['♠', '♥', '♦', '♣']
        self.cartas = []
        self._crear_baraja()

    def _crear_baraja(self):
        """Inicializa la baraja con todas las cartas."""
        for palo in self.palos:
            for valor in self.valores:
                self.cartas.append(Carta(valor, palo))

    def mezclar(self, semilla=None):
        """Mezcla la baraja, opcionalmente usando una semilla para reproducibilidad."""
        if semilla is not None:
            random.seed(semilla)
        random.shuffle(self.cartas)

    def repartir_carta(self):
        """Reparte una carta de la parte superior de la baraja."""
        if not self.cartas:
            raise ValueError("¡No quedan cartas en la baraja!")
        return self.cartas.pop(0)

# --- Clase Jugador (base) ---
class Jugador:
    """Clase base para jugadores, tanto humanos como CPU."""
    def __init__(self, nombre, fichas_iniciales):
        self.nombre = nombre
        self.fichas = fichas_iniciales
        self.mano = [] # Cartas en la mano del jugador
        self.apostado_en_ronda = 0 # Fichas apostadas en la ronda actual
        self.esta_activo = True # Si el jugador no se ha retirado
        self.es_cpu = False

    def añadir_carta(self, carta):
        """Añade una carta a la mano del jugador."""
        self.mano.append(carta)

    def reset_mano(self):
        """Reinicia la mano y el estado de apuesta para una nueva ronda."""
        self.mano = []
        self.apostado_en_ronda = 0
        self.esta_activo = True

    def apostar(self, cantidad):
        """
        Realiza una apuesta.
        Devuelve True si la apuesta fue exitosa (o all-in), False si no fue posible.
        """
        if cantidad <= 0:
            # Una apuesta de 0 o menos no es válida, a menos que sea un "pasar"
            # Pero esta función es específicamente para apostar fichas.
            return False

        if cantidad > self.fichas:
            # Si no tiene suficientes fichas, va all-in con lo que tiene
            if self.fichas > 0:
                cantidad = self.fichas # Apuesta todas sus fichas restantes
                self.fichas -= cantidad
                self.apostado_en_ronda += cantidad
                return True # Indica que fue all-in
            else:
                # No tiene fichas para apostar, se retira
                self.retirarse()
                return False

        self.fichas -= cantidad
        self.apostado_en_ronda += cantidad
        return True

    def retirarse(self):
        """Marca al jugador como retirado de la ronda."""
        self.esta_activo = False

    def __str__(self):
        return f"{self.nombre} (Fichas: {self.fichas})"

# --- Clase CPU (hereda de Jugador) ---
class CPU(Jugador):
    """Implementa la lógica de decisión para el jugador CPU."""
    def __init__(self, nombre, fichas_iniciales):
        super().__init__(nombre, fichas_iniciales)
        self.es_cpu = True

    def decidir_accion(self, apuesta_actual, fichas_en_mesa):
        """
        Decide la acción de la CPU (apostar, igualar, subir, pasar, retirarse, all-in).
        Esta es una IA muy básica y puede ser mejorada.
        """
        cantidad_a_igualar = apuesta_actual - self.apostado_en_ronda

        # Si no hay apuesta que igualar (o ya ha igualado/está por encima)
        if cantidad_a_igualar <= 0:
            if random.random() < 0.7: # 70% de pasar
                return "pasar", 0
            else: # 30% de apostar
                apuesta = random.randint(MIN_APUESTA, 80)
                if self.fichas >= apuesta:
                    return "apostar", apuesta
                else:
                    return "pasar", 0 # No tiene fichas para apostar, entonces pasa
        else: # Hay una apuesta que igualar
            if self.fichas < cantidad_a_igualar: # No tiene suficientes fichas para igualar
                if self.fichas > 0 and random.random() < 0.3: # 30% de ir all-in si puede
                    return "all-in", self.fichas
                else: # 70% de retirarse
                    return "retirarse", 0
            else: # Puede igualar
                r = random.random()
                if r < 0.6: # 60% de igualar
                    return "igualar", cantidad_a_igualar
                elif r < 0.8: # 20% de subir
                    cantidad_subida = random.randint(MIN_APUESTA, 100)
                    if self.fichas >= cantidad_a_igualar + cantidad_subida:
                        return "subir", cantidad_a_igualar + cantidad_subida
                    else: # No puede subir, entonces iguala
                        return "igualar", cantidad_a_igualar
                else: # 20% de retirarse (conservador)
                    return "retirarse", 0

# --- Clase Mesa ---
class Mesa:
    """Representa la mesa de póker, incluyendo cartas comunitarias y el bote."""
    def __init__(self):
        self.cartas_comunitarias = []
        self.bote = 0

    def añadir_carta_comunitaria(self, carta):
        """Añade una carta a las cartas comunitarias."""
        self.cartas_comunitarias.append(carta)

    def añadir_al_bote(self, cantidad):
        """Añade fichas al bote principal."""
        self.bote += cantidad

    def reset_mesa(self):
        """Reinicia las cartas comunitarias y el bote para una nueva ronda."""
        self.cartas_comunitarias = []
        self.bote = 0

# --- Clase PokerGame (Lógica Principal del Juego) ---
class PokerGame:
    """Gestiona el estado y la lógica principal del juego de póker."""
    def __init__(self, nombre_jugador):
        self.baraja = Baraja()
        self.mesa = Mesa()
        self.jugador = Jugador(nombre_jugador, FICHAS_INICIALES)
        self.maquina = CPU("CPU", FICHAS_INICIALES)
        self.jugadores_en_juego = [self.jugador, self.maquina] # Orden de turnos
        self.apuesta_actual_ronda = 0 # La apuesta más alta que se ha hecho en la ronda actual
        self.turno_actual_index = 0 # Índice del jugador al que le toca el turno
        self.ronda_de_apuestas_actual = 0 # 0=Pre-flop, 1=Flop, 2=Turn, 3=River, 4=Showdown
        self.estado_juego = "inicio_ronda" # Controla el flujo del juego (ej. "pre_flop_apuestas", "showdown")
        self.mensaje_ronda = "" # Mensajes generales para el usuario
        self.mensaje_error = "" # Mensajes de error específicos para el usuario
        self.ultima_accion_cpu = "" # Para mostrar qué hizo la CPU

    def iniciar_ronda(self, semilla=None):
        """Inicia una nueva ronda de póker."""
        self.mensaje_ronda = "--- ¡Nueva Ronda de Póker! ---"
        self.mensaje_error = ""
        self.ultima_accion_cpu = ""

        # Reiniciar baraja, mesa y manos de los jugadores
        self.baraja = Baraja()
        self.mesa.reset_mesa()
        for jugador in self.jugadores_en_juego:
            jugador.reset_mano()

        self.apuesta_actual_ronda = 0
        self.turno_actual_index = 0 # El turno siempre empieza con el primer jugador en la lista
        self.ronda_de_apuestas_actual = 0 # Resetea a Pre-flop
        self.baraja.mezclar(semilla)

        # Repartir 2 cartas a cada jugador
        for _ in range(2):
            self.jugador.añadir_carta(self.baraja.repartir_carta())
            self.maquina.añadir_carta(self.baraja.repartir_carta())

        self.estado_juego = "pre_flop_apuestas" # El juego está en la fase de apuestas pre-flop
        self.mensaje_ronda = "Ronda de apuestas: Pre-Flop. ¡Cartas repartidas!"

    def avanzar_fase_juego(self):
        """Avanza el juego a la siguiente fase (Flop, Turn, River, Showdown)."""
        self.apuesta_actual_ronda = 0 # Reiniciar apuesta para la nueva fase
        for jugador in self.jugadores_en_juego:
            jugador.apostado_en_ronda = 0 # Reiniciar apuestas por ronda para la nueva fase

        self.mensaje_error = ""
        self.ultima_accion_cpu = ""

        # Si solo queda un jugador activo, la ronda termina por retiro
        if self.contar_jugadores_activos() <= 1:
            self.estado_juego = "ronda_terminada_por_retiro"
            self.determinar_ganador() # El único jugador activo gana el bote
            return

        if self.ronda_de_apuestas_actual == 0: # De Pre-flop a Flop
            self.ronda_de_apuestas_actual = 1
            self.baraja.repartir_carta() # Quema una carta
            for _ in range(3): # Reparte 3 cartas comunitarias
                self.mesa.añadir_carta_comunitaria(self.baraja.repartir_carta())
            self.estado_juego = "flop_apuestas"
            self.mensaje_ronda = "Ronda de apuestas: Flop. ¡Se han repartido las 3 primeras cartas comunitarias!"
        elif self.ronda_de_apuestas_actual == 1: # De Flop a Turn
            self.ronda_de_apuestas_actual = 2
            self.baraja.repartir_carta() # Quema una carta
            self.mesa.añadir_carta_comunitaria(self.baraja.repartir_carta()) # Reparte la 4ta carta
            self.estado_juego = "turn_apuestas"
            self.mensaje_ronda = "Ronda de apuestas: Turn. ¡Se ha repartido la cuarta carta comunitaria!"
        elif self.ronda_de_apuestas_actual == 2: # De Turn a River
            self.ronda_de_apuestas_actual = 3
            self.baraja.repartir_carta() # Quema una carta
            self.mesa.añadir_carta_comunitaria(self.baraja.repartir_carta()) # Reparte la 5ta carta
            self.estado_juego = "river_apuestas"
            self.mensaje_ronda = "Ronda de apuestas: River. ¡Se ha repartido la quinta y última carta comunitaria!"
        elif self.ronda_de_apuestas_actual == 3: # De River a Showdown
            self.ronda_de_apuestas_actual = 4 # Indicador de que ya estamos en Showdown
            self.estado_juego = "showdown"
            self.determinar_ganador() # Llama a la lógica del showdown
            self.mensaje_ronda = "¡SHOWDOWN! Es hora de comparar manos."
            return # No hay más turnos de apuestas después del showdown

        # Después de avanzar fase, el turno vuelve al inicio de los activos
        self.turno_actual_index = 0
        self._avanzar_a_siguiente_jugador_activo() # Asegurarse de que el turno actual sea de un jugador activo

    def _avanzar_a_siguiente_jugador_activo(self):
        """Avanza el turno al siguiente jugador activo en la lista."""
        start_index = self.turno_actual_index
        num_players = len(self.jugadores_en_juego)

        # Itera para encontrar el siguiente jugador activo
        for i in range(1, num_players + 1):
            next_index = (start_index + i) % num_players
            player = self.jugadores_en_juego[next_index]
            if player.esta_activo:
                self.turno_actual_index = next_index
                return
        # Si no se encuentra ningún jugador activo (todos se retiraron),
        # la lógica de _verificar_fin_ronda_apuestas debería manejarlo.

    def es_turno_jugador_humano(self):
        """Verifica si es el turno del jugador humano."""
        # Si solo queda un jugador activo, no hay más turnos de apuestas
        if self.contar_jugadores_activos() <= 1:
            return False
        return self.jugadores_en_juego[self.turno_actual_index] == self.jugador and self.jugador.esta_activo

    def es_turno_cpu(self):
        """Verifica si es el turno de la CPU."""
        if self.contar_jugadores_activos() <= 1:
            return False
        return self.jugadores_en_juego[self.turno_actual_index] == self.maquina and self.maquina.esta_activo

    def _ejecutar_turno_cpu(self):
        """Ejecuta la acción de la CPU."""
        self.mensaje_error = "" # Limpiar errores anteriores
        self.ultima_accion_cpu = "" # Limpiar la última acción

        accion_cpu, cantidad_cpu = self.maquina.decidir_accion(self.apuesta_actual_ronda, self.mesa.bote)
        self.ultima_accion_cpu = accion_cpu # Guardar la acción para mostrarla en el HTML

        if accion_cpu == "apostar":
            if self.maquina.apostar(cantidad_cpu):
                self.apuesta_actual_ronda = cantidad_cpu
                self.mesa.añadir_al_bote(cantidad_cpu)
                self.mensaje_ronda = f"{self.maquina.nombre} apuesta {cantidad_cpu} fichas."
            else:
                self.mensaje_ronda = f"{self.maquina.nombre} intentó apostar pero no pudo. {self.maquina.nombre} tiene {self.maquina.fichas} fichas."
        elif accion_cpu == "igualar":
            if self.maquina.apostar(cantidad_cpu):
                self.mesa.añadir_al_bote(cantidad_cpu)
                self.mensaje_ronda = f"{self.maquina.nombre} iguala la apuesta."
            else:
                self.mensaje_ronda = f"{self.maquina.nombre} intentó igualar pero no pudo. {self.maquina.nombre} tiene {self.maquina.fichas} fichas."
        elif accion_cpu == "subir":
            if self.maquina.apostar(cantidad_cpu):
                self.apuesta_actual_ronda = cantidad_cpu # La cantidad_cpu ya incluye la subida
                self.mesa.añadir_al_bote(cantidad_cpu)
                self.mensaje_ronda = f"{self.maquina.nombre} sube la apuesta a {self.apuesta_actual_ronda} fichas."
            else:
                self.mensaje_ronda = f"{self.maquina.nombre} intentó subir pero no pudo. {self.maquina.nombre} tiene {self.maquina.fichas} fichas."
        elif accion_cpu == "pasar":
            self.mensaje_ronda = f"{self.maquina.nombre} pasa."
        elif accion_cpu == "retirarse":
            self.maquina.retirarse()
            self.mensaje_ronda = f"{self.maquina.nombre} se ha retirado de la ronda."
        elif accion_cpu == "all-in":
            if self.maquina.apostar(cantidad_cpu):
                self.mesa.añadir_al_bote(cantidad_cpu)
                self.mensaje_ronda = f"{self.maquina.nombre} va ALL-IN con {cantidad_cpu} fichas."
            else:
                self.maquina.retirarse() # Si no pudo ir all-in, se retira
                self.mensaje_ronda = f"{self.maquina.nombre} intentó ir ALL-IN pero no pudo. Se retira."

        # Después de la acción de la CPU, avanza al siguiente jugador y verifica si la ronda de apuestas ha terminado
        self._avanzar_a_siguiente_jugador_activo()
        self._verificar_fin_ronda_apuestas()

    def manejar_accion_jugador(self, accion, cantidad=0):
        """Procesa la acción realizada por el jugador humano."""
        self.mensaje_error = "" # Limpiar errores anteriores
        self.ultima_accion_cpu = "" # Limpiar la última acción

        jugador = self.jugador

        if accion == "apostar":
            if self.apuesta_actual_ronda > 0:
                self.mensaje_error = "Ya hay una apuesta. Usa 'igualar' o 'subir'."
                return False
            if cantidad < MIN_APUESTA or cantidad > jugador.fichas:
                self.mensaje_error = f"Cantidad inválida. Debe ser al menos {MIN_APUESTA} y no exceder tus fichas ({jugador.fichas})."
                return False
            if jugador.apostar(cantidad):
                self.apuesta_actual_ronda = cantidad
                self.mesa.añadir_al_bote(cantidad)
                self.mensaje_ronda = f"{jugador.nombre} ha apostado {cantidad} fichas."
            else:
                self.mensaje_error = "No pudiste apostar esa cantidad."
                return False

        elif accion == "igualar":
            if self.apuesta_actual_ronda == 0:
                self.mensaje_error = "No hay apuesta que igualar. Usa 'pasar' o 'apostar'."
                return False
            cantidad_a_igualar = self.apuesta_actual_ronda - jugador.apostado_en_ronda
            if cantidad_a_igualar <= 0:
                self.mensaje_ronda = "Ya has igualado o estás por encima de la apuesta actual."
            else:
                if jugador.apostar(cantidad_a_igualar):
                    self.mesa.añadir_al_bote(cantidad_a_igualar)
                    self.mensaje_ronda = f"{jugador.nombre} iguala la apuesta."
                else:
                    self.mensaje_error = "No pudiste igualar la apuesta."
                    return False

        elif accion == "subir":
            if self.apuesta_actual_ronda == 0:
                self.mensaje_error = "No hay apuesta para subir. Usa 'apostar'."
                return False
            if cantidad < MIN_APUESTA:
                self.mensaje_error = f"La cantidad a subir debe ser al menos {MIN_APUESTA}."
                return False
            
            # La cantidad total a apostar es lo que ya apostó + la diferencia para igualar + la subida
            cantidad_para_igualar = self.apuesta_actual_ronda - jugador.apostado_en_ronda
            cantidad_total_a_apostar = cantidad_para_igualar + cantidad

            if cantidad_total_a_apostar > jugador.fichas:
                self.mensaje_error = f"No tienes suficientes fichas para subir esa cantidad. Necesitas {cantidad_total_a_apostar}, tienes {jugador.fichas}."
                return False

            if jugador.apostar(cantidad_total_a_apostar):
                self.apuesta_actual_ronda = self.apuesta_actual_ronda + cantidad # La nueva apuesta es la anterior + la subida
                self.mesa.añadir_al_bote(cantidad_total_a_apostar)
                self.mensaje_ronda = f"{jugador.nombre} ha subido la apuesta a {self.apuesta_actual_ronda} fichas."
            else:
                self.mensaje_error = "No pudiste subir la apuesta."
                return False

        elif accion == "pasar":
            if self.apuesta_actual_ronda > 0:
                self.mensaje_error = "No puedes pasar, hay una apuesta pendiente. Debes igualar, subir o retirarte."
                return False
            self.mensaje_ronda = f"{jugador.nombre} pasa."

        elif accion == "retirarse":
            jugador.retirarse()
            self.mensaje_ronda = f"{jugador.nombre} se ha retirado de la ronda."

        else:
            self.mensaje_error = "Acción inválida. Inténtalo de nuevo."
            return False

        # Si la acción fue exitosa, avanza al siguiente turno y verifica el fin de la ronda
        self._avanzar_a_siguiente_jugador_activo()
        self._verificar_fin_ronda_apuestas()

        return True # La acción se procesó correctamente

    def _verificar_fin_ronda_apuestas(self):
        """
        Verifica si la ronda de apuestas actual ha terminado.
        Una ronda de apuestas termina si:
        1. Solo queda un jugador activo (gana el bote inmediatamente).
        2. Todos los jugadores activos han igualado la apuesta_actual_ronda (o ido all-in por menos).
        """
        jugadores_activos = [p for p in self.jugadores_en_juego if p.esta_activo]

        if len(jugadores_activos) <= 1:
            self.estado_juego = "ronda_terminada_por_retiro"
            return True

        todos_igualados = True
        for p in jugadores_activos:
            # Un jugador ha "igualado" si su apuesta en esta ronda es igual a la apuesta actual
            # O si ha ido all-in y no tiene más fichas, y su apuesta es menor que la actual
            if p.apostado_en_ronda < self.apuesta_actual_ronda and p.fichas > 0:
                todos_igualados = False
                break
            # Si un jugador fue all-in y su apostado_en_ronda es menor que apuesta_actual_ronda,
            # pero ya no tiene fichas, se considera que ha "igualado" lo máximo posible.
            if p.apostado_en_ronda < self.apuesta_actual_ronda and p.fichas == 0:
                pass # Este jugador ya no puede apostar más, está "igualado" en su all-in

        if todos_igualados:
            self.estado_juego = "ronda_apuestas_completa"
            return True
        
        return False # La ronda de apuestas aún no ha terminado

    def contar_jugadores_activos(self):
        """Devuelve el número de jugadores activos en la ronda."""
        return sum(1 for p in self.jugadores_en_juego if p.esta_activo)

    # --- Lógica de Evaluación de Manos de Póker ---
    # Los rangos de manos se devuelven como una tupla (valor_de_rango, kickers...)
    # Esto permite una fácil comparación: una tupla mayor significa una mano mejor.

    def _get_hand_rank(self, five_cards):
        """
        Evalúa una mano de 5 cartas y devuelve su rango.
        Ranks:
        9: Escalera Real de Color (Royal Flush)
        8: Escalera de Color (Straight Flush)
        7: Póker (Four of a Kind)
        6: Full House
        5: Color (Flush)
        4: Escalera (Straight)
        3: Trío (Three of a Kind)
        2: Doble Pareja (Two Pair)
        1: Pareja (Pair)
        0: Carta Alta (High Card)
        """
        # Ordenar cartas por rango para facilitar la evaluación
        # El As (14) puede ser bajo (1) para la escalera A-2-3-4-5
        sorted_cards = sorted(five_cards, key=lambda c: c.valor_rank, reverse=True)
        ranks = [c.valor_rank for c in sorted_cards]
        suits = [c.palo for c in sorted_cards]

        # Contar ocurrencias de cada rango
        rank_counts = {}
        for rank in ranks:
            rank_counts[rank] = rank_counts.get(rank, 0) + 1

        # Verificar si es color (Flush)
        is_flush = len(set(suits)) == 1

        # Verificar si es escalera (Straight)
        is_straight, high_straight_rank = self._is_straight(ranks)

        # 9. Escalera Real de Color (Royal Flush)
        if is_flush and is_straight and high_straight_rank == 14: # A, K, Q, J, 10 del mismo palo
            return (9, ranks)

        # 8. Escalera de Color (Straight Flush)
        if is_flush and is_straight:
            return (8, (high_straight_rank,)) # El kicker es la carta más alta de la escalera

        # 7. Póker (Four of a Kind)
        if 4 in rank_counts.values():
            quad_rank = [rank for rank, count in rank_counts.items() if count == 4][0]
            kicker = [rank for rank in ranks if rank != quad_rank][0]
            return (7, (quad_rank, kicker))

        # 6. Full House
        if 3 in rank_counts.values() and 2 in rank_counts.values():
            triple_rank = [rank for rank, count in rank_counts.items() if count == 3][0]
            pair_rank = [rank for rank, count in rank_counts.items() if count == 2][0]
            return (6, (triple_rank, pair_rank))

        # 5. Color (Flush)
        if is_flush:
            return (5, ranks) # Los kickers son los rangos de las 5 cartas en orden descendente

        # 4. Escalera (Straight)
        if is_straight:
            return (4, (high_straight_rank,)) # El kicker es la carta más alta de la escalera

        # 3. Trío (Three of a Kind)
        if 3 in rank_counts.values():
            triple_rank = [rank for rank, count in rank_counts.items() if count == 3][0]
            kickers = sorted([rank for rank in ranks if rank != triple_rank], reverse=True)
            return (3, (triple_rank, kickers[0], kickers[1]))

        # 2. Doble Pareja (Two Pair)
        if list(rank_counts.values()).count(2) == 2:
            pair_ranks = sorted([rank for rank, count in rank_counts.items() if count == 2], reverse=True)
            kicker = [rank for rank in ranks if rank not in pair_ranks][0]
            return (2, (pair_ranks[0], pair_ranks[1], kicker))

        # 1. Pareja (Pair)
        if 2 in rank_counts.values():
            pair_rank = [rank for rank, count in rank_counts.items() if count == 2][0]
            kickers = sorted([rank for rank in ranks if rank != pair_rank], reverse=True)
            return (1, (pair_rank, kickers[0], kickers[1], kickers[2]))

        # 0. Carta Alta (High Card)
        return (0, ranks) # Los kickers son los rangos de las 5 cartas en orden descendente

    def _is_straight(self, ranks):
        """
        Verifica si un conjunto de rangos forma una escalera.
        Devuelve (True, high_card_rank) si es escalera, (False, 0) si no.
        Maneja la escalera A-2-3-4-5 (donde A es 1).
        """
        unique_ranks = sorted(list(set(ranks))) # Ordenar de menor a mayor
        
        # Caso normal: 5 cartas consecutivas
        if len(unique_ranks) >= 5:
            for i in range(len(unique_ranks) - 4):
                if unique_ranks[i+4] - unique_ranks[i] == 4:
                    return True, unique_ranks[i+4] # Retorna la carta más alta de la escalera

        # Caso especial: A-2-3-4-5 (Ace como 1)
        # Convertir As (14) a 1 para esta verificación
        low_ace_ranks = [1 if r == 14 else r for r in ranks]
        low_ace_unique_ranks = sorted(list(set(low_ace_ranks)))
        if set([1, 2, 3, 4, 5]).issubset(set(low_ace_unique_ranks)):
            return True, 5 # La carta más alta es el 5

        return False, 0

    def _get_best_hand(self, player_cards, community_cards):
        """
        Dadas las 2 cartas del jugador y las 5 comunitarias,
        encuentra la mejor mano de 5 cartas de las 7 disponibles.
        """
        all_seven_cards = player_cards + community_cards
        best_rank = (-1, []) # Inicializar con un rango muy bajo

        # Generar todas las combinaciones posibles de 5 cartas de las 7
        for five_cards_combo in itertools.combinations(all_seven_cards, 5):
            current_rank = self._get_hand_rank(list(five_cards_combo))
            if current_rank > best_rank: # Las tuplas se comparan elemento a elemento
                best_rank = current_rank
        return best_rank

    def determinar_ganador(self):
        """
        Determina el ganador de la ronda.
        Si solo queda un jugador activo, ese jugador gana.
        De lo contrario, evalúa las manos de póker completas.
        """
        jugadores_activos = [p for p in self.jugadores_en_juego if p.esta_activo]

        if len(jugadores_activos) == 1:
            ganador = jugadores_activos[0]
            self.mensaje_ronda = f"¡Todos los demás jugadores se han retirado! ¡{ganador.nombre} gana el bote de {self.mesa.bote} fichas!"
            ganador.fichas += self.mesa.bote
            self.mesa.reset_mesa()
            self.estado_juego = "ronda_finalizada" # La ronda ha terminado, se puede iniciar una nueva
            return

        # Evaluar las mejores manos de 5 cartas para cada jugador
        player_best_hand_rank = self._get_best_hand(self.jugador.mano, self.mesa.cartas_comunitarias)
        cpu_best_hand_rank = self._get_best_hand(self.maquina.mano, self.mesa.cartas_comunitarias)

        ganador = None
        mensaje_ganador = ""

        if player_best_hand_rank > cpu_best_hand_rank:
            ganador = self.jugador
            mensaje_ganador = f"¡{self.jugador.nombre} gana con {self._hand_rank_to_name(player_best_hand_rank[0])}!"
        elif cpu_best_hand_rank > player_best_hand_rank:
            ganador = self.maquina
            mensaje_ganador = f"¡{self.maquina.nombre} gana con {self._hand_rank_to_name(cpu_best_hand_rank[0])}!"
        else:
            # Empate: el bote se divide. En este caso, asignamos el bote a un jugador aleatorio
            # o podrías implementar una lógica para dividir el bote si es posible.
            ganador = random.choice([self.jugador, self.maquina])
            mensaje_ganador = f"¡SHOWDOWN! ¡Es un empate! Ambos tienen {self._hand_rank_to_name(player_best_hand_rank[0])}. El bote se asigna a {ganador.nombre}."

        self.mensaje_ronda = mensaje_ganador + f"\n¡{ganador.nombre} se lleva el bote de {self.mesa.bote} fichas!"
        ganador.fichas += self.mesa.bote
        self.mesa.reset_mesa()
        self.estado_juego = "ronda_finalizada" # La ronda ha terminado

    def _hand_rank_to_name(self, rank_value):
        """Convierte el valor numérico del rango de la mano a un nombre legible."""
        names = {
            9: "Escalera Real de Color",
            8: "Escalera de Color",
            7: "Póker",
            6: "Full House",
            5: "Color",
            4: "Escalera",
            3: "Trío",
            2: "Doble Pareja",
            1: "Pareja",
            0: "Carta Alta"
        }
        return names.get(rank_value, "Mano Desconocida")


# --- Configuración y Rutas de Flask ---
app = Flask(__name__)
# ADVERTENCIA DE SEGURIDAD:
# La clave secreta es VITAL para la seguridad de las sesiones de Flask.
# ¡Cámbiala por una cadena larga y aleatoria en un entorno de producción!
# Genera una con: os.urandom(24).hex()
app.secret_key = 'tu_clave_secreta_super_segura_y_aleatoria_aqui_!@#$%'   
juego_en_curso = {} # Diccionario para almacenar el juego por nombre de jugador (ID de sesión)

@app.route('/')
def index():
    """Ruta principal del juego. Muestra la pantalla de inicio o la mesa de juego."""
    # Si el jugador no ha introducido su nombre, muestra la pantalla de inicio
    if 'nombre_jugador' not in session:
        return render_template('inicio.html')

    nombre_jugador = session['nombre_jugador']
    # Si el juego no está en curso para este jugador, inicialízalo
    if nombre_jugador not in juego_en_curso:
        juego_en_curso[nombre_jugador] = PokerGame(nombre_jugador)
        juego_en_curso[nombre_jugador].iniciar_ronda() # Inicia la primera ronda

    juego = juego_en_curso[nombre_jugador]

    # Si es el turno de la CPU y el juego está en una fase de apuestas, ejecuta su acción
    if juego.es_turno_cpu() and juego.estado_juego in ["pre_flop_apuestas", "flop_apuestas", "turn_apuestas", "river_apuestas"]:
        juego._ejecutar_turno_cpu()
        # Redirige para que la página se recargue y muestre el nuevo estado
        # Esto es una forma simple de manejar el turno de la CPU en Flask sin AJAX/WebSockets.
        return redirect(url_for('index'))

    # Renderiza la plantilla principal del juego con el estado actual
    return render_template('juego.html',
                           juego=juego, # Pasar el objeto juego completo
                           jugador=juego.jugador,
                           maquina=juego.maquina,
                           mesa=juego.mesa,
                           apuesta_actual_ronda=juego.apuesta_actual_ronda,
                           mensaje_ronda=juego.mensaje_ronda,
                           mensaje_error=juego.mensaje_error,
                           ultima_accion_cpu=juego.ultima_accion_cpu,
                           # Mapeo de números de ronda a nombres legibles
                           ronda_nombre={0: "Pre-Flop", 1: "Flop", 2: "Turn", 3: "River", 4: "Showdown"}.get(juego.ronda_de_apuestas_actual, "Desconocida")
                           )

@app.route('/iniciar_juego', methods=['POST'])
def iniciar_juego_post():
    """Maneja el envío del formulario de nombre de jugador."""
    nombre_jugador = request.form['nombre']
    if not nombre_jugador.strip(): # Validar que el nombre no esté vacío
        return render_template('inicio.html', error="Por favor, introduce un nombre válido.")

    session['nombre_jugador'] = nombre_jugador
    return redirect(url_for('index'))

@app.route('/nueva_ronda', methods=['POST'])
def nueva_ronda():
    """Inicia una nueva ronda de juego."""
    nombre_jugador = session.get('nombre_jugador')
    if nombre_jugador and nombre_jugador in juego_en_curso:
        juego = juego_en_curso[nombre_jugador]
        entrada_semilla = request.form.get('semilla', '').strip()
        semilla = int(entrada_semilla) if entrada_semilla.isdigit() else None
        juego.iniciar_ronda(semilla)
    return redirect(url_for('index'))

@app.route('/realizar_accion', methods=['POST'])
def realizar_accion():
    """Procesa la acción (apostar, igualar, subir, pasar, retirarse) del jugador humano."""
    nombre_jugador = session.get('nombre_jugador')
    if not nombre_jugador or nombre_jugador not in juego_en_curso:
        return redirect(url_for('index'))

    juego = juego_en_curso[nombre_jugador]

    accion = request.form.get('accion')
    cantidad_str = request.form.get('cantidad', '').strip()
    cantidad = 0

    if cantidad_str:
        try:
            cantidad = int(cantidad_str)
            if cantidad < 0: # Asegurarse de que la cantidad no sea negativa
                raise ValueError
        except ValueError:
            juego.mensaje_error = "Cantidad inválida. Por favor, introduce un número entero positivo."
            return redirect(url_for('index'))

    # Solo permite al jugador humano realizar acciones si es su turno y el juego está en fase de apuestas
    if juego.es_turno_jugador_humano() and juego.estado_juego in ["pre_flop_apuestas", "flop_apuestas", "turn_apuestas", "river_apuestas"]:
        juego.manejar_accion_jugador(accion, cantidad)
    else:
        juego.mensaje_error = "No es tu turno o la acción no es válida en este momento."

    return redirect(url_for('index'))

@app.route('/avanzar_fase', methods=['POST'])
def avanzar_fase():
    """Avanza el juego a la siguiente fase (Flop, Turn, River, Showdown)."""
    nombre_jugador = session.get('nombre_jugador')
    if not nombre_jugador or nombre_jugador not in juego_en_curso:
        return redirect(url_for('index'))

    juego = juego_en_curso[nombre_jugador]

    # Solo se puede avanzar de fase si la ronda de apuestas actual está completa
    if juego._verificar_fin_ronda_apuestas() and juego.estado_juego not in ["showdown", "ronda_finalizada", "ronda_terminada_por_retiro"]:
        juego.avanzar_fase_juego()
    else:
        juego.mensaje_error = "La ronda de apuestas actual no ha terminado aún o el juego ya ha finalizado."

    return redirect(url_for('index'))

# --- Ejecución del Servidor Flask ---
if __name__ == '__main__':
    # Para ejecutar: python app.py
    # Luego abre tu navegador en http://127.0.0.1:5000/
    # debug=True recarga automáticamente el servidor y muestra errores detallados.
    app.run(debug=True)
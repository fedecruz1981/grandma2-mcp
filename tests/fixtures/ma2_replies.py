# Respuestas REALES de grandMA2 onPC 3.9.60.82 (show "joel nuevos cct 2026"),
# capturadas por telnet el 2026-10-14. ANSI preservado tal cual llega.
#
# Razón de existir: los tests de este repo se escribieron con respuestas
# inventadas ("1  Cue1") que NO coinciden con lo que manda la consola
# ("Cue 1 1  *  Go"). Los parsers no matchearon ni una fila real hasta que
# estas capturas los Corrientes.
#
# python scripts/sonda_parsers_vs_repo.py regenera esto contra una consola viva.

LIST_SEQUENCE = (
    "Executing : \x1b[32mList\x1b[37m \x1b[32mSequence\x1b[37m\r\n\r\n"
    "\x1b[32m        No.  Name                    Track  ReleaseFirststep"
    "  CueZero  CueZeroExtract  InputFilter \x1b[37m\r\n\r\n"
    "Sequ   1 1    Sequ                    On     On                Off"
    "      Off             None         \r\n\r\n"
    "Sequ   2 2    Sequ                    On     On                Off"
    "      Off             None         \r\n\r\n"
    "Sequ   3 3    DIMER BEAM              On     On                Off"
    "      Off             None         \r\n\r\n"
    " \x1b[32mMacro\x1b[37m>\x1b[K"
)

LIST_MACRO = (
    "Executing : \x1b[32mList\x1b[37m \x1b[32mMacro\x1b[37m\r\n\r\n"
    "\x1b[32m        No.  Name                   CLI  Timing  Info\x1b[37m\r\n\r\n"
    "Macro 1 1    Stomp Position         On   On             (1)\r\n\r\n"
    "Macro 2 2    Stomp Color            On   On             (1)\r\n\r\n"
    "Macro 3 3    Stomp Beam             On   On             (1)\r\n\r\n"
    " \x1b[32mMacro\x1b[37m>\x1b[K"
)

# La 156 tiene un solo cue. Ojo con el prefijo "Cue " y el MIB repetido.
LIST_CUE_SEQUENCE = (
    "Executing : \x1b[32mList\x1b[37m \x1b[32mCue\x1b[37m \x1b[32mSequence\x1b[37m 156\r\n\r\n"
    "\x1b[32m      Number  MIB  Trig  TrigTime  Mode    Loop  Lcount    Ltime"
    "     \x1b[37m\r\n\r\n"
    "Cue 1 1       *    Go              Normal  None  Infinite  Infinite   (1)\r\n\r\n"
    " \x1b[32mMacro\x1b[37m>\x1b[K"
)

LIST_CUE_ONE = (
    "Executing : \x1b[32mList\x1b[37m \x1b[32mCue\x1b[37m 1 \x1b[32mSequence\x1b[37m 156\r\n\r\n"
    "\x1b[32m      Number  MIB  Trig  TrigTime  Mode    Loop  Lcount    Ltime"
    "     \x1b[37m\r\n\r\n"
    "Cue 1 1       *    Go              Normal  None  Infinite  Infinite   (1)\r\n\r\n"
    " \x1b[32mMacro\x1b[37m>\x1b[K"
)

# Un cue con varios cues y uno de ellos con decimal, para ejercitar el parser.
# Compuesto a mano desde el formato observado: la consola emite una fila por
# cue con el mismo prefijo "Cue ".
LIST_CUE_SEQUENCE_MULTI = (
    "Executing : \x1b[32mList\x1b[37m \x1b[32mCue\x1b[37m \x1b[32mSequence\x1b[37m 161\r\n\r\n"
    "\x1b[32m      Number  MIB  Trig  TrigTime  Mode    Loop  Lcount    Ltime"
    "     \x1b[37m\r\n\r\n"
    "Cue 1 1       *    Go              Normal  None  Infinite  Infinite   (1)\r\n\r\n"
    "Cue 2 2       *    Go              Normal  None  Infinite  Infinite   (2)\r\n\r\n"
    "Cue 3.1 3     *    Go              Normal  None  Infinite  Infinite   (3)\r\n\r\n"
    "Cue 10 10     *    Go              Normal  None  Infinite  Infinite   (4)\r\n\r\n"
    " \x1b[32mMacro\x1b[37m>\x1b[K"
)

LIST_FIXTURE = (
    "Executing : \x1b[32mList\x1b[37m \x1b[32mFixture\x1b[37m\r\n\r\n"
    "\x1b[32m                   LibraryName             ScreenName"
    "          Universal  IdentifiedAs     \x1b[37m\r\n\r\n"
    "Fixture 1 1    Mac700 Profile          Mac700 Front         Off        Dimmer -> Profile\r\n\r\n"
    "Fixture 2 2    Mac700 Profile          Mac700 Front         Off        Dimmer -> Profile\r\n\r\n"
    " \x1b[32mMacro\x1b[37m>\x1b[K"
)

LIST_PRESET_POOL = (
    "Executing : \x1b[32mList\x1b[37m \x1b[32mPreset\x1b[37m 1\r\n\r\n"
    "\x1b[32m         No.  Name      Special  Info\x1b[37m\r\n\r\n"
    "Beam 5.1 5.1  SN FROST  Normal\r\n\r\n"
    " \x1b[32mMacro\x1b[37m>\x1b[K"
)

NO_OBJECTS = (
    "Executing : \x1b[32mList\x1b[37m \x1b[32mCue\x1b[37m 999"
    " \x1b[32mSequence\x1b[37m 156\r\n\r\n"
    "WARNING, NO OBJECTS FOUND FOR LIST\r\n\r\n"
    " \x1b[32mMacro\x1b[37m>\x1b[K"
)

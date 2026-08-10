import streamlit as st
import requests
import os
import tempfile
import time
import ctranslate2

from faster_whisper import WhisperModel


# ==================================================
# PUSLAPIS
# ==================================================

st.title("Apps'o pavadinimas")

st.write("Įkelkite garso failą transkribavimui.")


# ==================================================
# VARIKLIO PASIRINKIMAS
# ==================================================

variklis = st.radio(
    "Transkribavimo variklis",
    [
        "Deepgram Nova-3",
        "Whisper large-v3",
        "Abu – palyginti"
    ]
)


# ==================================================
# KALBOS PASIRINKIMAS
# ==================================================

kalbos = {
    "Automatiškai": "auto",
    "Lietuvių": "lt",
    "Rusų": "ru"
}

pasirinkta_kalba = st.selectbox(
    "Pasirinkite garso kalbą",
    list(kalbos.keys())
)


# ==================================================
# DEEPGRAM
# ==================================================

def deepgram_garso_i_teksta(audio_file, kalba):

    url = "https://api.deepgram.com/v1/listen"

    if kalba == "auto":

        params = [
            ("model", "nova-3-general"),
            ("detect_language", "lt"),
            ("detect_language", "ru"),
            ("smart_format", "true")
        ]

    else:

        params = {
            "model": "nova-3-general",
            "language": kalba,
            "smart_format": "true"
        }

    headers = {
        "Authorization":
            f"Token {st.secrets['DEEPGRAM_API_KEY']}",
        "Content-Type": audio_file.type
    }

    pradzia = time.perf_counter()

    response = requests.post(
        url,
        params=params,
        headers=headers,
        data=audio_file.getvalue(),
        timeout=300
    )

    apdorojimo_laikas = (
        time.perf_counter() - pradzia
    )

    if response.status_code != 200:

        raise Exception(
            f"Deepgram klaida "
            f"{response.status_code}: "
            f"{response.text}"
        )

    rezultatas = response.json()

    channel = (
        rezultatas["results"]["channels"][0]
    )

    alternative = (
        channel["alternatives"][0]
    )

    tekstas = alternative.get(
        "transcript",
        ""
    )

    transkripcijos_patikimumas = (
        alternative.get(
            "confidence",
            None
        )
    )

    if kalba == "auto":

        aptikta_kalba = channel.get(
            "detected_language",
            "nežinoma"
        )

        kalbos_patikimumas = channel.get(
            "language_confidence",
            None
        )

    else:

        aptikta_kalba = kalba
        kalbos_patikimumas = None

    trukme = rezultatas.get(
        "metadata",
        {}
    ).get(
        "duration",
        0
    )

    return {
        "tekstas": tekstas,
        "kalba": aptikta_kalba,
        "kalbos_patikimumas":
            kalbos_patikimumas,
        "transkripcijos_patikimumas":
            transkripcijos_patikimumas,
        "trukme": trukme,
        "apdorojimo_laikas":
            apdorojimo_laikas
    }


# ==================================================
# WHISPER LARGE-V3
# ==================================================

@st.cache_resource
def uzkrauti_whisper_modeli():

    # NVIDIA GPU
    if ctranslate2.get_cuda_device_count() > 0:

        return WhisperModel(
            "large-v3",
            device="cuda",
            compute_type="float16"
        )

    # CPU
    return WhisperModel(
        "large-v3",
        device="cpu",
        compute_type="float32"
    )


def whisper_garso_i_teksta(
    audio_file,
    kalba
):

    modelis = uzkrauti_whisper_modeli()

    failo_galune = os.path.splitext(
        audio_file.name
    )[1]

    with tempfile.NamedTemporaryFile(
        delete=False,
        suffix=failo_galune
    ) as temp_file:

        temp_file.write(
            audio_file.getvalue()
        )

        temp_kelias = temp_file.name

    try:

        if kalba == "auto":
            whisper_kalba = None
        else:
            whisper_kalba = kalba

        pradzia = time.perf_counter()

        segments, info = modelis.transcribe(

            temp_kelias,

            language=whisper_kalba,

            task="transcribe",

            # Kokybei
            beam_size=5,

            temperature=0.0,

            condition_on_previous_text=True,

            # Žodžių probabilities
            word_timestamps=True,

            # Kad nedarytų problemų dainoms
            vad_filter=False
        )

        # Transkripcija realiai atliekama
        # iteruojant generatorių
        segments = list(segments)

        apdorojimo_laikas = (
            time.perf_counter() - pradzia
        )


        # ------------------------------------------
        # TEKSTAS
        # ------------------------------------------

        teksto_dalys = []

        for segmentas in segments:

            segment_text = (
                segmentas.text.strip()
            )

            if segment_text:

                teksto_dalys.append(
                    segment_text
                )

        visas_tekstas = " ".join(
            teksto_dalys
        )


        # ------------------------------------------
        # VIDUTINĖ ŽODŽIŲ TIKIMYBĖ
        # ------------------------------------------

        zodziu_patikimumai = []

        for segmentas in segments:

            if segmentas.words:

                for zodis in segmentas.words:

                    if (
                        zodis.probability
                        is not None
                    ):

                        zodziu_patikimumai.append(
                            zodis.probability
                        )

        if zodziu_patikimumai:

            transkripcijos_patikimumas = (
                sum(zodziu_patikimumai)
                /
                len(zodziu_patikimumai)
            )

        else:

            transkripcijos_patikimumas = None


        return {
            "tekstas":
                visas_tekstas,

            "kalba":
                info.language,

            "kalbos_patikimumas":
                info.language_probability,

            "transkripcijos_patikimumas":
                transkripcijos_patikimumas,

            "trukme":
                info.duration,

            "apdorojimo_laikas":
                apdorojimo_laikas
        }

    finally:

        if os.path.exists(temp_kelias):
            os.remove(temp_kelias)


# ==================================================
# REZULTATO RODYMAS
# ==================================================

def rodyti_rezultata(
    pavadinimas,
    rezultatas,
    kalbos_kodas,
    download_key
):

    st.subheader(pavadinimas)

    if rezultatas is None:
        return

    if kalbos_kodas == "auto":

        st.write(
            f"Aptikta kalba: "
            f"**{rezultatas['kalba']}**"
        )

        if (
            rezultatas[
                "kalbos_patikimumas"
            ]
            is not None
        ):

            st.write(
                "Kalbos aptikimo "
                "patikimumas: "
                f"**{rezultatas['kalbos_patikimumas']:.2%}**"
            )

    else:

        st.write(
            f"Pasirinkta kalba: "
            f"**{kalbos_kodas}**"
        )

    if (
        rezultatas[
            "transkripcijos_patikimumas"
        ]
        is not None
    ):

        st.write(
            "Modelio patikimumo rodiklis: "
            f"**{rezultatas['transkripcijos_patikimumas']:.2%}**"
        )

    st.write(
        f"Garso trukmė: "
        f"**{rezultatas['trukme']:.1f} s**"
    )

    st.write(
        f"Transkribavimo laikas: "
        f"**{rezultatas['apdorojimo_laikas']:.1f} s**"
    )

    tekstas = rezultatas["tekstas"]

    if tekstas.strip():

        st.text_area(
            "Transkribuotas tekstas",
            value=tekstas,
            height=400,
            key=f"text_{download_key}"
        )

        st.download_button(
            "Atsisiųsti tekstą",
            data=tekstas,
            file_name=(
                f"transkriptas_"
                f"{download_key}.txt"
            ),
            mime="text/plain",
            key=f"download_{download_key}"
        )

    else:

        st.warning(
            "Modelis apdorojo failą, "
            "bet neatpažino teksto."
        )


# ==================================================
# FAILO ĮKĖLIMAS
# ==================================================

ikeltas_garso_failas = st.file_uploader(
    "Įkelkite garso failą",
    type=[
        "mp3",
        "wav",
        "m4a",
        "ogg",
        "flac"
    ]
)


if ikeltas_garso_failas is not None:

    st.audio(ikeltas_garso_failas)

    if st.button(
        "Transkribuoti",
        type="primary"
    ):

        kalbos_kodas = kalbos[
            pasirinkta_kalba
        ]

        st.session_state[
            "deepgram_rezultatas"
        ] = None

        st.session_state[
            "whisper_rezultatas"
        ] = None

        st.session_state[
            "deepgram_klaida"
        ] = None

        st.session_state[
            "whisper_klaida"
        ] = None


        # ==========================================
        # DEEPGRAM
        # ==========================================

        if variklis in [
            "Deepgram Nova-3",
            "Abu – palyginti"
        ]:

            with st.spinner(
                "Deepgram transkribuoja..."
            ):

                try:

                    st.session_state[
                        "deepgram_rezultatas"
                    ] = deepgram_garso_i_teksta(
                        ikeltas_garso_failas,
                        kalbos_kodas
                    )

                except Exception as e:

                    st.session_state[
                        "deepgram_klaida"
                    ] = str(e)


        # ==========================================
        # WHISPER
        # ==========================================

        if variklis in [
            "Whisper large-v3",
            "Abu – palyginti"
        ]:

            with st.spinner(
                "Whisper large-v3 "
                "transkribuoja..."
            ):

                try:

                    st.session_state[
                        "whisper_rezultatas"
                    ] = whisper_garso_i_teksta(
                        ikeltas_garso_failas,
                        kalbos_kodas
                    )

                except Exception as e:

                    st.session_state[
                        "whisper_klaida"
                    ] = str(e)


# ==================================================
# REZULTATŲ RODYMAS
# ==================================================

if variklis == "Abu – palyginti":

    col1, col2 = st.columns(2)

    with col1:

        if st.session_state.get(
            "deepgram_klaida"
        ):

            st.error(
                "Deepgram klaida: "
                + st.session_state[
                    "deepgram_klaida"
                ]
            )

        elif st.session_state.get(
            "deepgram_rezultatas"
        ):

            rodyti_rezultata(
                "Deepgram Nova-3",
                st.session_state[
                    "deepgram_rezultatas"
                ],
                kalbos[
                    pasirinkta_kalba
                ],
                "deepgram"
            )

    with col2:

        if st.session_state.get(
            "whisper_klaida"
        ):

            st.error(
                "Whisper klaida: "
                + st.session_state[
                    "whisper_klaida"
                ]
            )

        elif st.session_state.get(
            "whisper_rezultatas"
        ):

            rodyti_rezultata(
                "Whisper large-v3",
                st.session_state[
                    "whisper_rezultatas"
                ],
                kalbos[
                    pasirinkta_kalba
                ],
                "whisper"
            )


elif variklis == "Deepgram Nova-3":

    if st.session_state.get(
        "deepgram_klaida"
    ):

        st.error(
            "Deepgram klaida: "
            + st.session_state[
                "deepgram_klaida"
            ]
        )

    elif st.session_state.get(
        "deepgram_rezultatas"
    ):

        rodyti_rezultata(
            "Deepgram Nova-3",
            st.session_state[
                "deepgram_rezultatas"
            ],
            kalbos[
                pasirinkta_kalba
            ],
            "deepgram"
        )


elif variklis == "Whisper large-v3":

    if st.session_state.get(
        "whisper_klaida"
    ):

        st.error(
            "Whisper klaida: "
            + st.session_state[
                "whisper_klaida"
            ]
        )

    elif st.session_state.get(
        "whisper_rezultatas"
    ):

        rodyti_rezultata(
            "Whisper large-v3",
            st.session_state[
                "whisper_rezultatas"
            ],
            kalbos[
                pasirinkta_kalba
            ],
            "whisper"
        )
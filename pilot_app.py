
import streamlit as st
import pandas as pd
import random
import re
import time
from pathlib import Path
from datetime import datetime


# ============================================================
# STUDY SETTINGS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

AUDIO_FOLDER = BASE_DIR / "Pilot" / "Generated Audios"
RESULTS_FOLDER = BASE_DIR / "Pilot" / "Results"

EXPECTED_SONGS = [
    "Someone Like You",
    "Washing Machine Heart",
    "Young Dumb & Broke"
]

TOTAL_TRIALS = 36


# ============================================================
# PAGE SETUP
# ============================================================

st.set_page_config(
    page_title="Spatial Hearing Study",
    page_icon="🎧",
    layout="centered"
)


# ============================================================
# FIND AUDIO FILES
# ============================================================

pattern = re.compile(
    r"Level_(\d+)_(\d+(?:\.\d+)?)ms_(LR|RL)\.wav$"
)

trials = []

if AUDIO_FOLDER.exists():

    for file in AUDIO_FOLDER.rglob("*.wav"):

        match = pattern.match(file.name)

        if match:

            level = int(match.group(1))
            itd_ms = float(match.group(2))
            direction = match.group(3)
            song = file.parent.name

            trials.append({
                "song": song,
                "level": level,
                "itd_ms": itd_ms,
                "direction": direction,
                "file": str(file)
            })


# ============================================================
# VERIFY AUDIO
# ============================================================

if len(trials) != TOTAL_TRIALS:

    st.error(
        f"The study could not find the expected {TOTAL_TRIALS} audio files."
    )

    st.write(
        f"Found {len(trials)} audio files."
    )

    st.write(
        "Please check the Generated Audios folders before continuing."
    )

    st.stop()


# ============================================================
# SESSION STATE
# ============================================================

defaults = {
    "started": False,
    "participant_id": "",
    "trial_list": [],
    "current_trial": 0,
    "results": [],
    "trial_start_time": None,
    "finished": False
}

for key, value in defaults.items():

    if key not in st.session_state:
        st.session_state[key] = value


# ============================================================
# START PAGE
# ============================================================

if not st.session_state.started:

    st.title("Spatial Hearing Study")

    st.write("### Welcome")

    st.write(
        """
        Thanks for taking part in this study.

        You’ll hear short clips of music and decide which direction
        the vocals are moving.
        """
    )

    st.write("### Instructions")

    st.write(
        """
        For each trial:

        1. Listen to the music clip.
        2. Decide whether the vocals move from **left to right**
           or from **right to left**.
        3. Select the answer that best matches what you heard.

        You can listen to a clip more than once if you need to.
        There are 36 trials in total. Please make your best judgment
        on each trial.
        """
    )

    st.write("")

    participant_id = st.text_input(
        "Participant ID",
        placeholder="Example: P001"
    )

    st.caption(
        "Please use the participant ID provided by the researcher."
    )

    if st.button(
        "Begin Study",
        type="primary",
        use_container_width=True
    ):

        if participant_id.strip() == "":

            st.warning(
                "Please enter your Participant ID before beginning."
            )

        else:

            st.session_state.participant_id = participant_id.strip()

            randomized_trials = trials.copy()
            random.shuffle(randomized_trials)

            st.session_state.trial_list = randomized_trials
            st.session_state.current_trial = 0
            st.session_state.results = []
            st.session_state.trial_start_time = None
            st.session_state.finished = False
            st.session_state.started = True

            st.rerun()

    st.stop()


# ============================================================
# COMPLETION PAGE
# ============================================================

if st.session_state.finished:

    st.title("Study Complete")

    st.write("### Thank you for participating.")

    st.write(
        "You have completed all 36 trials."
    )

    st.write(
        "Your responses have been recorded."
    )

    st.write(
        "You may now close this window."
    )

    st.stop()


# ============================================================
# CURRENT TRIAL
# ============================================================

trial_number = st.session_state.current_trial + 1

total_trials = len(
    st.session_state.trial_list
)

trial = st.session_state.trial_list[
    st.session_state.current_trial
]


# ============================================================
# TRIAL DISPLAY
# ============================================================

st.title("Spatial Hearing Study")

st.write(
    f"**Trial {trial_number} of {total_trials}**"
)

st.progress(
    trial_number / total_trials
)

st.write("")

st.write(
    "### Listen to the audio"
)

st.audio(
    trial["file"],
    format="audio/wav"
)

st.write("")

st.write(
    "### Which direction did the vocal sound move?"
)


# ============================================================
# START RESPONSE TIMER
# ============================================================

if st.session_state.trial_start_time is None:

    st.session_state.trial_start_time = time.time()


# ============================================================
# RESPONSE BUTTONS
# ============================================================

col1, col2 = st.columns(2)

with col1:

    left_to_right = st.button(
        "←  LEFT → RIGHT",
        use_container_width=True
    )

with col2:

    right_to_left = st.button(
        "RIGHT → LEFT  →",
        use_container_width=True
    )


# ============================================================
# PROCESS RESPONSE
# ============================================================

response = None

if left_to_right:

    response = "LR"

elif right_to_left:

    response = "RL"


if response is not None:

    response_time = (
        time.time()
        - st.session_state.trial_start_time
    )

    correct = (
        response == trial["direction"]
    )

    result = {
        "participant_id": st.session_state.participant_id,
        "trial": trial_number,
        "song": trial["song"],
        "itd_ms": trial["itd_ms"],
        "actual_direction": trial["direction"],
        "participant_response": response,
        "correct": correct,
        "response_time_seconds": response_time,
        "timestamp": datetime.now().isoformat()
    }

    st.session_state.results.append(result)

    st.session_state.current_trial += 1

    st.session_state.trial_start_time = None

    # --------------------------------------------------------
    # FINISH AND SAVE
    # --------------------------------------------------------

    if (
        st.session_state.current_trial
        >= total_trials
    ):

        RESULTS_FOLDER.mkdir(
            parents=True,
            exist_ok=True
        )

        timestamp = datetime.now().strftime(
            "%Y%m%d_%H%M%S"
        )

        filename = (
            f"{st.session_state.participant_id}_"
            f"{timestamp}.csv"
        )

        results_df = pd.DataFrame(
            st.session_state.results
        )

        results_df.to_csv(
            RESULTS_FOLDER / filename,
            index=False
        )

        st.session_state.finished = True

    st.rerun()

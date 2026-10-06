import streamlit as st
import pandas as pd
import random
import re
import time
import requests
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

# ============================================================
# ITD LEVELS
# ============================================================

# Easy block
EASY_ITDS = [
    3.0,
    2.5,
    2.0
]

# Moderate block
MODERATE_ITDS = [
    1.5,
    1.25,
    1.0
]

# Difficult block
DIFFICULT_ITDS = [
    0.75,
    0.5,
    0.25
]

ITD_BLOCKS = [
    EASY_ITDS,
    MODERATE_ITDS,
    DIFFICULT_ITDS
]

TRIALS_PER_ITD = 4

TOTAL_TRIALS = (
    9 * TRIALS_PER_ITD
)


# ============================================================
# GOOGLE SHEETS CONNECTION
# ============================================================

GOOGLE_SCRIPT_URL = st.secrets.get(
    "GOOGLE_SCRIPT_URL",
    "https://docs.google.com/spreadsheets/d/1m3bjqIX7VzRWnr5qeejmkAvnHEuISryzEc-WDEKvOiE/edit?usp=sharing"
)


def save_to_google_sheet(result):

    if not GOOGLE_SCRIPT_URL:
        return False

    try:

        response = requests.post(
            GOOGLE_SCRIPT_URL,
            json=result,
            timeout=10
        )

        return response.status_code == 200

    except Exception as e:

        print("Google Sheets error:", e)

        return False


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
# VERIFY AUDIO FILE COUNT
# ============================================================

EXPECTED_AUDIO_FILES = 9 * 3 * 2

if len(trials) != EXPECTED_AUDIO_FILES:

    st.error(
        f"The study could not find the expected "
        f"{EXPECTED_AUDIO_FILES} audio files."
    )

    st.write(
        f"Found {len(trials)} audio files."
    )

    st.write(
        "Please check the Generated Audios folders "
        "before continuing."
    )

    st.stop()


# ============================================================
# VERIFY SONGS
# ============================================================

found_songs = sorted(
    set(
        trial["song"]
        for trial in trials
    )
)

missing_songs = [
    song
    for song in EXPECTED_SONGS
    if song not in found_songs
]

if missing_songs:

    st.error(
        "The following expected songs were not found:"
    )

    for song in missing_songs:
        st.write(f"- {song}")

    st.stop()


# ============================================================
# VERIFY ITD LEVELS
# ============================================================

expected_itds = set(
    EASY_ITDS
    + MODERATE_ITDS
    + DIFFICULT_ITDS
)

found_itds = set(
    trial["itd_ms"]
    for trial in trials
)

missing_itds = sorted(
    expected_itds - found_itds,
    reverse=True
)

if missing_itds:

    st.error(
        "The following expected ITD levels were not found:"
    )

    for itd in missing_itds:
        st.write(f"- {itd} ms")

    st.stop()


# ============================================================
# CREATE PARTICIPANT TRIAL LIST
# ============================================================

def create_trial_list():

    participant_trials = []

    for block_itds in ITD_BLOCKS:

        block_trials = []

        for itd in block_itds:

            # ------------------------------------------------
            # Find all audio files for this ITD
            # ------------------------------------------------

            itd_trials = [
                trial
                for trial in trials
                if trial["itd_ms"] == itd
            ]

            # ------------------------------------------------
            # Four trials per ITD:
            # 2 left-to-right
            # 2 right-to-left
            #
            # All three songs are represented.
            # One song appears twice.
            # ------------------------------------------------

            extra_song = random.choice(
                EXPECTED_SONGS
            )

            songs_for_level = (
                EXPECTED_SONGS.copy()
            )

            songs_for_level.append(
                extra_song
            )

            # Randomize which song receives which direction
            random.shuffle(songs_for_level)

            directions = [
                "LR",
                "RL",
                "LR",
                "RL"
            ]

            random.shuffle(directions)

            selected_trials = []

            for song, direction in zip(
                songs_for_level,
                directions
            ):

                matching_trials = [
                    trial
                    for trial in itd_trials
                    if (
                        trial["song"] == song
                        and
                        trial["direction"] == direction
                    )
                ]

                if not matching_trials:

                    st.error(
                        f"Could not find audio for "
                        f"{song}, {itd} ms, {direction}."
                    )

                    st.stop()

                selected_trial = random.choice(
                    matching_trials
                )

                selected_trials.append(
                    selected_trial
                )

            # Randomize the four trials for this ITD
            random.shuffle(selected_trials)

            block_trials.extend(
                selected_trials
            )

        # Randomize the 12 trials within this block
        random.shuffle(block_trials)

        participant_trials.extend(
            block_trials
        )

    return participant_trials


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

        You’ll hear short clips of music and decide which
        direction the vocals are moving.
        """
    )

    st.write("### Instructions")

    st.write(
        """
        For each trial:

        1. Listen to the music clip.
        2. Decide whether the vocals move from
           **left to right** or from **right to left**.
        3. Select the answer that best matches what you heard.

        You can listen to a clip more than once if you need to.

        There are 36 trials in total. Please make your best
        judgment on each trial.
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

            st.session_state.participant_id = (
                participant_id.strip()
            )

            # Create this participant's 36 trials
            participant_trials = create_trial_list()

            st.session_state.trial_list = (
                participant_trials
            )

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

    st.write(
        "### Thank you for participating."
    )

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

trial_number = (
    st.session_state.current_trial + 1
)

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

    # --------------------------------------------------------
    # SAVE RESULT IN SESSION
    # --------------------------------------------------------

    st.session_state.results.append(result)

    # --------------------------------------------------------
    # SEND RESULT TO GOOGLE SHEETS
    # --------------------------------------------------------

    save_to_google_sheet(result)

    # --------------------------------------------------------
    # ADVANCE TRIAL
    # --------------------------------------------------------

    st.session_state.current_trial += 1

    st.session_state.trial_start_time = None

    # --------------------------------------------------------
    # FINISH AND SAVE LOCAL BACKUP
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

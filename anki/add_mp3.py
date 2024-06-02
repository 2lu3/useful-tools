#!/usr/bin/env python3
import requests
import os
from dataclasses import dataclass
from google.cloud import texttospeech
import shutil
from loguru import logger
from argparse import ArgumentParser


@dataclass
class Note:
    index: int
    front: str
    back: str
    sound: str


def get_client():
    client = texttospeech.TextToSpeechClient()
    return client


def fetch_notes(deck_name: str) -> list:
    res = requests.post(
        "http://localhost:8765",
        json={
            "action": "findNotes",
            "version": 6,
            "params": {"query": f"deck:{deck_name}"},
        },
    ).json()

    assert res["error"] is None

    return res["result"]


def fetch_note(note_id):
    res = requests.post(
        "http://localhost:8765",
        json={"action": "notesInfo", "version": 6, "params": {"notes": [note_id]}},
    ).json()

    assert res["error"] is None

    note_info = res["result"][0]

    return Note(
        index=note_info["noteId"],
        front=note_info["fields"]["表面"]["value"],
        back=note_info["fields"]["裏面"]["value"],
        sound=note_info["fields"]["音声"]["value"],
    )


def update_note_sound(note: Note, sound_path: str):
    res = requests.post(
        "http://localhost:8765",
        json={
            "action": "updateNoteFields",
            "version": 6,
            "params": {"note": {"id": note.index, "fields": {"音声": sound_path}}},
        },
    )
    assert res.json()["error"] is None


def generate_sound(client, text: str):
    synthesis_input = texttospeech.SynthesisInput(text=text)

    voice = texttospeech.VoiceSelectionParams(
        language_code="en-US", ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
    )

    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3
    )

    res = client.synthesize_speech(
        input=synthesis_input, voice=voice, audio_config=audio_config
    )

    with open("output.mp3", "wb") as out:
        out.write(res.audio_content)


def main(deck_name: str, is_delete: bool):
    ANKI_MEDIA_PATH = (
        f"/home/{os.getlogin()}/.local/share/Anki2/ユーザー 1/collection.media"
    )

    client = get_client()

    note_indexes = fetch_notes(deck_name)

    if is_delete:
        for index in note_indexes:
            note = fetch_note(index)
            if note.sound != "":
                os.remove(os.path.join(ANKI_MEDIA_PATH, note.sound))
                update_note_sound(note, "")
                logger.debug(f"Deleted {note.back}")
        return


    for index in note_indexes:
        note = fetch_note(index)
        if note.sound != "":
            logger.info(
                f"Skipping {note.front} {note.back} because it already has sound"
            )
            continue

        if note.back == "":
            logger.warning(f"Skipping {note.front} {note.back} because it has no back")
            continue
        generate_sound(client, note.back)
        shutil.move("output.mp3", os.path.join(ANKI_MEDIA_PATH, f"{note.back}.mp3"))
        update_note_sound(note, f"[sound:{note.back}.mp3]")
        logger.debug(f"Updated {note.back}")


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("deck", help="Deck name")
    parser.add_argument("--delete", help="Delete all mp3 files", action="store_true")
    args = parser.parse_args()

    main(args.deck, args.delete)

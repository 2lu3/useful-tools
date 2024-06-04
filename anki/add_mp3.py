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


class Anki:
    def __init__(self):
        self.media_path = (
            f"/home/{os.getlogin()}/.local/share/Anki2/ユーザー 1/collection.media"
        )
        self.url = "http://localhost:8765"

    def fetch_notes(self, deck_name: str) -> list[Note]:
        res = requests.post(
            self.url,
            json={
                "action": "findNotes",
                "version": 6,
                "params": {"query": f"deck:{deck_name}"},
            },
        ).json()

        assert res["error"] is None

        indexes = res["result"]

        return [self._fetch_note(index) for index in indexes]

    def update_field(self, note: Note, field: str, value: str):
        res = requests.post(
            "http://localhost:8765",
            json={
                "action": "updateNoteFields",
                "version": 6,
                "params": {"note": {"id": note.index, "fields": {field: value}}},
            },
        )
        assert res.json()["error"] is None

        return res.json()["result"]

    def add_sound_field(self, note: Note, file_path: str):
        shutil.move(file_path, os.path.join(self.media_path, f"{note.back}.mp3"))
        self.update_field(note, "音声", f"[sound:{note.back}.mp3]")

    def remove_sound_field(self, note: Note):
        os.remove(os.path.join(self.media_path, note.sound))
        self.update_field(note, "音声", "")

    def validate_not_nbsp(self, note: Note):
        if "&nbsp;" in note.front:
            self.update_field(note, "表面", note.front.replace("&nbsp;", " "))
        if "&nbsp;" in note.back:
            self.update_field(note, "裏面", note.back.replace("&nbsp;", " "))

    def _fetch_note(self, note_id: int) -> Note:
        res = requests.post(
            self.url,
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


def delete_mp3(deck_name: str):
    anki = Anki()
    for note in anki.fetch_notes(deck_name):
        if note.sound != "":
            anki.remove_sound_field(note)
            logger.debug(f"Deleted {note.back}")
        else:
            logger.info(
                f"Skipping {note.front} {note.back} because it doesn't have sound"
            )


def add_mp3(client, deck_name: str):
    anki = Anki()
    for note in anki.fetch_notes(deck_name):
        if note.sound == f"[sound:{note.back}.mp3]":
            logger.info(
                f"Skipping {note.front} {note.back} because it already has sound"
            )
            continue

        if note.back == "":
            logger.warning(f"Skipping {note.front} {note.back} because it has no back")
            continue
        generate_sound(client, note.back)
        anki.add_sound_field(note, "output.mp3")
        logger.debug(f"Updated {note.back}")

def validate_not_nbsp(deck_name: str):
    anki = Anki()
    for note in anki.fetch_notes(deck_name):
        anki.validate_not_nbsp(note)


def main(deck_name: str, is_delete: bool):
    client = texttospeech.TextToSpeechClient()

    validate_not_nbsp(deck_name)

    if is_delete:
        delete_mp3(deck_name)
        return
    else:
        add_mp3(client, deck_name)
        return


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("deck", help="Deck name")
    parser.add_argument("--delete", help="Delete all mp3 files", action="store_true")
    args = parser.parse_args()

    main(args.deck, args.delete)

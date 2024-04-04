#!/usr/bin/env python
import json
import os
from typing import Any
from typing import Dict
from typing import List

import requests
from le_utils.constants.labels import levels
from le_utils.constants.labels import subjects
from ricecooker.chefs import SushiChef
from ricecooker.classes.files import DocumentFile
from ricecooker.classes.files import HTMLZipFile
from ricecooker.classes.licenses import get_license
from ricecooker.classes.nodes import ChannelNode
from ricecooker.classes.nodes import DocumentNode
from ricecooker.classes.nodes import HTML5AppNode
from ricecooker.classes.nodes import TopicNode
from ricecooker.config import LOGGER
from ricecooker.utils.zip import create_predictable_zip

from transform import download_gdrive_files
from transform import prepare_lesson_html5_directory
from transform import unzip_scorm_files

CHANNEL_NAME = "Digitalize your business"
CHANNEL_SOURCE_ID = "ilo-dyb"
SOURCE_DOMAIN = "https://www.ilo.org/empent/areas/start-and-improve-your-business/WCMS_914727/lang--en/index.htm"  # noqa: E501
CHANNEL_LANGUAGE = "en"
CHANNEL_DESCRIPTION = "This online self-guided course discusses the basic requirements and main steps for getting any existing or future business online."  # noqa: E501
CHANNEL_THUMBNAIL = "chefdata/ilo_dyb.png"
CONTENT_ARCHIVE_VERSION = 1

CHANNEL_LICENSE = get_license(
    "CC BY-SA", copyright_holder="International Labour Organization"
)
SESSION = requests.Session()

categories: List[str] = [
    subjects.TECHNICAL_AND_VOCATIONAL_TRAINING,
    subjects.ENTREPRENEURSHIP,
    subjects.FINANCIAL_LITERACY,
    subjects.PROFESSIONAL_SKILLS,
]

grade_levels: List[str] = [
    levels.PROFESSIONAL,
    levels.WORK_SKILLS,
]


class ILODYBChef(SushiChef):
    channel_info: Dict[str, str] = {
        "CHANNEL_SOURCE_DOMAIN": SOURCE_DOMAIN,
        "CHANNEL_SOURCE_ID": CHANNEL_SOURCE_ID,
        "CHANNEL_TITLE": CHANNEL_NAME,
        "CHANNEL_LANGUAGE": CHANNEL_LANGUAGE,
        "CHANNEL_THUMBNAIL": CHANNEL_THUMBNAIL,
        "CHANNEL_DESCRIPTION": CHANNEL_DESCRIPTION,
    }

    def download_content(self) -> None:
        LOGGER.info("Downloading needed files from Google Drive folders")
        download_gdrive_files()
        LOGGER.info("Uncompressing courses in scorm format")
        unzip_scorm_files()
        # create html5app nodes for each lesson
        for course in self.course_data.keys():
            course_dir = course.replace(" ", "_").lower()
            for lesson in self.course_data[course]:
                lesson_dir = os.path.join(f"chefdata/{course_dir}/{lesson}")
                if not os.path.exists(lesson_dir):  # create lesson app dir
                    lesson_data = self.course_data[course][lesson]
                    prepare_lesson_html5_directory(lesson_data, lesson_dir)
                LOGGER.info(
                    f"Creating zip for lesson: {lesson} in course {course}"  # noqa: E501
                )
                self.course_data[course][lesson][
                    "zipfile"
                ] = create_predictable_zip(  # noqa: E501
                    lesson_dir
                )  # noqa: E501

    def pre_run(self, args: Any, options: dict) -> None:
        self.course_data = json.load(open("chefdata/course_data.json"))
        LOGGER.info("Downloading files from Google Drive folders")

    def build_doc_node(
        self, doc: str, lesson_title: str, lesson_file: str
    ) -> DocumentNode:
        unit = lesson_title.split(" - ")[0]
        doc_name = doc.replace(".pdf", "")
        doc_node = DocumentNode(
            source_id=f"{doc_name.replace(' ', '_')}_id",
            title=f"{unit} forms: {doc_name}",
            files=[
                DocumentFile(
                    f"chefdata/{lesson_file}/scormcontent/assets/{doc}"
                )  # noqa: E501
            ],  # noqa: E501
            license=CHANNEL_LICENSE,
            language="en",
            categories=categories,
            grade_levels=grade_levels,
        )
        return doc_node

    def construct_channel(self, *args, **kwargs) -> ChannelNode:
        channel = self.get_channel(*args, **kwargs)
        for course in self.course_data.keys():
            course_dir = course.replace(" ", "_").lower()
            topic_node = TopicNode(
                source_id=f"{course_dir}_id",
                title=course,
                categories=categories,
                grade_levels=levels,
                derive_thumbnail=True,
                language=CHANNEL_LANGUAGE,
                author="International Labour Organization",
            )
            for lesson in self.course_data[course]:
                lesson_data = self.course_data[course][lesson]
                zip_file = lesson_data["zipfile"]
                zip_node = HTML5AppNode(
                    source_id="{}_{}_id".format(
                        course_dir, lesson.replace(" ", "_")
                    ),  # noqa: E501
                    title=lesson_data["title"],
                    files=[HTMLZipFile(zip_file)],
                    license=CHANNEL_LICENSE,
                    language="en",
                    categories=categories,
                    grade_levels=levels,
                )
                topic_node.add_child(zip_node)
                if "docs" in lesson_data.keys():
                    for doc in lesson_data["docs"]:
                        doc_node = self.build_doc_node(
                            doc, lesson_data["title"], lesson_data["file"]
                        )  # noqa: E501
                        topic_node.add_child(doc_node)

            channel.add_child(topic_node)
        return channel


if __name__ == "__main__":
    chef = ILODYBChef()
    chef.main()

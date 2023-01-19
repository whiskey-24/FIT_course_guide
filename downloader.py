import sys
import numpy as np
from bs4 import BeautifulSoup
from urllib.request import urlopen
import pickle
import os
from pprint import pprint
from dataclasses import dataclass, field
from typing import List, Dict
from collections import defaultdict


@dataclass
class Course:
    abbrv: str = ""
    name: str = ""
    garant: str = ""
    link: str = ""
    semester: str = ""
    credits: int = 0
    dept: str = ""
    finals: str = ""
    number_of_hours: Dict = field(default_factory=lambda: defaultdict(dict))
    points_dist: Dict = field(default_factory=lambda: defaultdict(dict))


def download_courses():
    page = urlopen("https://www.fit.vut.cz/study/courses/.cs?year=2022&type=NMgr")
    html = page.read().decode("utf-8")
    soup = BeautifulSoup(html, "html.parser")
    main = soup.find("main")

    courses = []
    course_rows = main.find("table", {"id": "list"}).find("tbody").find_all("tr")
    for row in course_rows:
        cells = row.find_all("td")

        course = Course()
        course.link = cells[0].find("a")["href"]
        course.name = cells[0].text
        course.abbrv = cells[1].text
        course.semester = cells[2].text
        course.credits = cells[3].text
        course.finals = cells[4].text
        course.dept = cells[5].text

        courses.append(course)

    for course in courses:
        page = urlopen(course.link)
        html = page.read().decode("utf-8")
        soup = BeautifulSoup(html, "html.parser")

        course.garant = soup.find("p", text=lambda t: t and "Garant" in t).parent.find_next_sibling("div").find("div").text.strip()

        try:
            hours = soup.find("p", text=lambda t: t and "Rozsah" in t).parent.find_next_sibling("div").find("div").text.strip()
            for co in hours.split(","):
                course.number_of_hours[co.strip()[8:]] = int(co.strip().split(" ")[0])
        except AttributeError:
            print(f"{course.abbrv} don't have hours")

        try:
            points = soup.find("p", text=lambda t: t and "Bodov" in t).parent.find_next_sibling("div").find("div").text.strip()
            for co in points.split(","):
                splitted = co.strip().split(" ")
                course.points_dist[" ".join(splitted[2:])] = int(splitted[0])
        except AttributeError:
            print(f"{course.abbrv} don't have bodove hodnotenie")

    return courses


if __name__ == "__main__":
    courses_file = "courses.pkl"
    specializations_file = "specializations.pkl"

    # Load courses
    if os.path.exists(courses_file):
        with open(courses_file, "rb") as f:
            courses = pickle.load(f)
        courses_dict = {x.abbrv: x for x in courses}
    else:
        courses = download_courses()
        with open(courses_file, "wb") as f:
            pickle.dump(courses, f)



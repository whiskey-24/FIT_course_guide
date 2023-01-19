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


@dataclass
class Spec:
    abbrv: str = ""
    link: str = ""
    name: str = ""
    garant: str = ""
    req: list[list[str]] = field(default_factory=list)
    req_any: list[list[str]] = field(default_factory=list)
    req_all: set = field(default_factory=set)


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


def get_all_required(all_tr):
    required = []
    for row in all_tr:
        cells = row.find_all("td")
        if cells[2].text == "P":
            required.append(row.find_all("th")[0].text)
    return required


def download_specializations():
    page = urlopen("https://www.fit.vut.cz/study/program/7887/.cs")
    html = page.read().decode("utf-8")
    soup = BeautifulSoup(html, "html.parser")
    main = soup.find("main")

    specializations = []
    spec_rows = main.find("div", {"class": "table-responsive__holder"}).find("tbody").find_all("tr")
    for row in spec_rows:
        cells = row.find_all("td")

        spec = Spec()
        spec.link = cells[0].find("a")["href"]
        spec.name = cells[0].text
        spec.abbrv = cells[1].text
        specializations.append(spec)

    # with open("links.pkl", "wb") as f:
    #     pickle.dump(specializations, f)
    #
    # with open("links.pkl", "rb") as f:
    #     specializations = pickle.load(f)

    for spec in specializations:
        print(spec.abbrv)
        page = urlopen(spec.link)
        html = page.read().decode("utf-8")
        soup = BeautifulSoup(html, "html.parser")

        spec.garant = soup.find("div", text=lambda
            t: t and "Garant" in t).parent.find_next_sibling("div").find(
            "a").text.strip()

        tables = soup.find("div", {"class": "table-responsive__holder"}).findChildren("table")
        for x in range(4):
            courses = get_all_required(tables[x].find("tbody").find_all("tr"))
            spec.req.append(courses)
            spec.req_all.update(courses)
        for x in range(2):
            courses = get_all_required(tables[4+x].find("tbody").find_all("tr"))
            spec.req_any.append(courses)
            spec.req_all.update(courses)

    return specializations


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

    # Load specializations
    if os.path.exists(specializations_file):
        with open(specializations_file, "rb") as f:
            specs = pickle.load(f)
        spec_dict = {x.abbrv: x for x in specs}
    else:
        specs = download_specializations()
        with open(specializations_file, "wb") as f:
            pickle.dump(specs, f)


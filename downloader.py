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
        course.credits = int(cells[3].text)
        course.finals = cells[4].text
        course.dept = cells[5].text

        courses.append(course)

    for course in courses:
        print("Downloading:", course.abbrv)
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

    for spec in specializations:
        print("Downloading:", spec.abbrv)
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


class FITCourseGuide:

    def __init__(self, courses_file, specializations_file):

        # Load courses
        if os.path.exists(courses_file):
            with open(courses_file, "rb") as f:
                self.courses = pickle.load(f)
            self.courses_dict = {x.abbrv: x for x in self.courses}
        else:
            self.courses = download_courses()
            with open(courses_file, "wb") as f:
                pickle.dump(self.courses, f)
            self.courses_dict = {x.abbrv: x for x in self.courses}

        # Load specializations
        if os.path.exists(specializations_file):
            with open(specializations_file, "rb") as f:
                self.specs = pickle.load(f)
            self.spec_dict = {x.abbrv: x for x in self.specs}
        else:
            self.specs = download_specializations()
            with open(specializations_file, "wb") as f:
                pickle.dump(self.specs, f)
            self.spec_dict = {x.abbrv: x for x in self.specs}

        # TODO after rerun
        for course in self.courses:
            course.credits = int(course.credits)

    def help_me_decide(self, spec_name):
        selected_courses = ["FCE", "FIT"]
        self.selected_spec = self.spec_dict[spec_name]

        print(f"{self.selected_spec.abbrv}, {self.selected_spec.name}\n"
              f"{self.selected_spec.garant}\n")
        self.print_semesters(self.selected_spec.req)

    def generate_matrix(self):
        req_all = set()
        for spec in self.specs:
            req_all.update(spec.req_all)

        out = "Spec\Course,"
        for req in req_all:
            out += f"{req},"
        out = out[:-1]
        out += "\n"
        for idx, spec in enumerate(self.specs):
            out += f"{spec.abbrv},"
            for req in req_all:
                if req in spec.req_all:
                    out += "1,"
                else:
                    out += "0,"

            out = out[:-1]
            out += "\n"

        with open("matrix.csv", "w") as f:
            f.write(out)

    def color_print_course(self):
    def print_semesters(self, selected_courses):
        total_credits = 0
        for x in range(4):
            if x % 2 == 0:
                idf = "W"
            else:
                idf = "S"
            sem_credits = sum(
                [self.courses_dict[x].credits for x in selected_courses[x]])
            total_credits += sem_credits
            print(f"{x // 2 + 1}. {idf}: {sem_credits:02} cr. {selected_courses[x]}")
        print(f"{total_credits}/120 cr.")


if __name__ == "__main__":
    FITCourseGuide("courses.pkl", "specializations.pkl")

    FITCourseGuide.help_me_decide("NVIZ")

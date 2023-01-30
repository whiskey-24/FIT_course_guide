from copy import deepcopy
from bs4 import BeautifulSoup
from urllib.request import urlopen
import pickle
import os
from dataclasses import dataclass, field
from typing import Dict
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


# Source https://svn.blender.org/svnroot/bf-blender/trunk/blender/build_files/scons/tools/bcolors.py
class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    RED = "\033[31m"
    GREEN = "\033[32m"
    WHITE = "\033[00m"
    CYAN = "\033[36m"
    MAGENTA = "\033[35m"
    PROJ = "\033[38;5;80m"
    TEST = "\033[38;5;162m"
    FINALS = "\033[38;5;160m"
    LECT = "\033[38;5;38m"
    LAB = "\033[38;5;38m"
    EMPTY = "\033["


class FITCourseGuide:
    W = 0  # Winter semester
    S = 1  # Summer semester

    def __init__(self, courses_file, specializations_file):

        # Load courses
        if os.path.exists(courses_file):
            with open(courses_file, "rb") as f:
                self.courses = pickle.load(f)
        else:
            self.courses = download_courses()
            with open(courses_file, "wb") as f:
                pickle.dump(self.courses, f)

        # Load specializations
        if os.path.exists(specializations_file):
            with open(specializations_file, "rb") as f:
                self.specs = pickle.load(f)
        else:
            self.specs = download_specializations()
            with open(specializations_file, "wb") as f:
                pickle.dump(self.specs, f)

        self.courses_dict = {}
        for course in self.courses:
            if course.abbrv not in self.courses_dict:
                self.courses_dict[course.abbrv] = course
            else:
                self.courses_dict[f"{course.abbrv}{self.courses_dict[course.abbrv].semester.lower()}"] = self.courses_dict[course.abbrv]
                del self.courses_dict[course.abbrv]
                self.courses_dict[f"{course.abbrv}{course.semester.lower()}"] = course

        self.spec_dict = {x.abbrv: x for x in self.specs}

    def help_me_decide(self, spec_name, selected_courses, cesa, legend=True):
        self.selected_spec = self.spec_dict[spec_name]
        spec_required = deepcopy(self.selected_spec.req)

        print(f"{self.selected_spec.abbrv}, {self.selected_spec.name}\n"
              f"{self.selected_spec.garant}\n\n"
              f"Only required courses:")
        self.print_semesters(spec_required, False)

        for idx, sem in enumerate(spec_required):
            sem.extend(selected_courses[idx])
        print("\nWith selected courses:")
        self.print_semesters(spec_required, True, cesa)

        if legend:
            print("\nLegend\nRequired:")
            for req in self.selected_spec.req_all:
                print(f"{req} - {self.courses_dict[req].name}")
            print("Optional:")
            flat_opt = [item for sublist in selected_courses for item in sublist]
            flat_opt = set(flat_opt) - set(self.selected_spec.req_all)
            for opt in flat_opt:
                print(f"{opt} - {self.courses_dict[opt].name}")

    def overview_of_specs(self):
        for spec in self.specs:
            self.selected_spec = spec
            print(f"\n{'#' * 70}\n\n"
                  f"{bcolors.HEADER}{self.selected_spec.abbrv}, "
                  f"{self.selected_spec.name}{bcolors.ENDC}\n"
                  f"{self.selected_spec.garant}\n\n"
                  f"Required courses:")
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

    def course_print_check(self, selected_courses, semester, detail=False):
        out = ""
        detail_points = "    : Points "
        detail_hours = "    : Hours  "
        # Points: proj/testy polsem/zk
        # Hours:  proj/lab a cvic/pred
        for course in selected_courses:
            course_obj = self.courses_dict[course]
            if course_obj.semester != semester:
                return f"{bcolors.FAIL}Course {course} in wrong semester " \
                       f"(W/S){bcolors.ENDC}"
            curr = ""
            if course in self.selected_spec.req_all:
                curr += f"{bcolors.WARNING}"
            else:
                curr += f"{bcolors.MAGENTA}"
            curr += f"{course}{bcolors.OKBLUE}" \
                    f"({self.courses_dict[course].finals})" \
                    f"{bcolors.ENDC}, "
            curr = curr.ljust(25)
            out += curr

            if not detail:
                continue

            hours = [
                sum([value for key, value in course_obj.number_of_hours.items()
                     if 'ojekty' in key.lower()]),  # Projects
                sum([value for key, value in course_obj.number_of_hours.items()
                     if 'abor' in key.lower() or 'cvi' in key.lower()]),  # Lab
                sum([value for key, value in course_obj.number_of_hours.items()
                     if 'edn' in key.lower()])      # Lectures
            ]
            detail_hours += f"{bcolors.PROJ}{hours[0]:02}/" \
                            f"{bcolors.LAB}{hours[1]:02}/" \
                            f"{bcolors.LECT}{hours[2]:02}" \
                            f"{bcolors.WHITE}   "

            points = [
                sum([value for key, value in course_obj.points_dist.items()
                     if 'ojekt' in key.lower()]),  # Projects
                sum([value for key, value in course_obj.points_dist.items()
                     if 'test' in key.lower()]),   # Tests
                sum([value for key, value in course_obj.points_dist.items()
                     if 'zkou' in key.lower()])    # Finals
            ]
            if max(points) == 100:
                detail_points += f"{bcolors.PROJ}{points[0]}/" \
                                 f"{bcolors.TEST}{points[1]}/" \
                                 f"{bcolors.FINALS}{points[2]}" \
                                 f"{bcolors.WHITE}    "
            else:
                detail_points += f"{bcolors.PROJ}{points[0]:02}/" \
                                 f"{bcolors.TEST}{points[1]:02}/" \
                                 f"{bcolors.FINALS}{points[2]:02}" \
                                 f"{bcolors.WHITE}   "

        if detail:
            return f"{out}\n{detail_points}\n{detail_hours}"
        else:
            return out

    def print_semesters(self, selected_courses, detail, cesa=0):
        total_credits = 0
        all_selected = set()
        for x in range(4):
            if x % 2 == 0:
                idf = "W"
            else:
                idf = "S"

            sem_credits = sum(
                [self.courses_dict[y].credits for y in selected_courses[x]])
            total_credits += sem_credits

            all_selected.update(selected_courses[x])
            print(f"{x // 2 + 1}. {idf}: {sem_credits:02} cr. "
                  f"{self.course_print_check(selected_courses[x], idf, detail)}"
                  f"{os.linesep if detail else ''}")

        if cesa != 0:
            print(f"CESA: {cesa} cr.")
            total_credits += cesa
        print_color_credits(total_credits)

        remaining = self.selected_spec.req_all - all_selected
        print(f"Remaining required: {len(remaining)}")
        if len(remaining) > 0:
            winter_rem = set(self.selected_spec.req_any[self.W]) - all_selected
            if len(winter_rem) > 0:
                winter_sum_rem = sum([self.courses_dict[x].credits for x in winter_rem])
                print(f"W: {winter_sum_rem} cr. "
                      f"{self.course_print_check(winter_rem, 'W')}")
            else:
                winter_sum_rem = 0

            summer_rem = set(self.selected_spec.req_any[self.S]) - all_selected
            if len(summer_rem):
                summer_sum_rem = sum([self.courses_dict[x].credits for x in summer_rem])
                print(f"S: {summer_sum_rem} cr. "
                      f"{self.course_print_check(summer_rem, 'S')}")
            else:
                summer_sum_rem = 0

            sum_rem = winter_sum_rem + summer_sum_rem
            print_color_credits(sum_rem + total_credits, f"({sum_rem}+{total_credits})")
        if detail:
            print("Color Legend:")
            print(f"Points: {bcolors.PROJ}Projects/"
                  f"{bcolors.TEST}Tests (half semester)/"
                  f"{bcolors.FINALS}Finals{bcolors.WHITE}\n"
                  f"Hours:  {bcolors.PROJ}Projects/"
                  f"{bcolors.LAB}Labs (exercises)/"
                  f"{bcolors.LECT}Lectures{bcolors.WHITE}")


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

        if cells[2].text == "L":
            course.semester = "S"
        else:
            course.semester = "W"

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


def print_color_credits(total_credits, hint=""):
    if total_credits < 120:
        print(f"{bcolors.RED}{hint}{total_credits}{bcolors.ENDC}", end="")
    else:
        print(f"{bcolors.GREEN}{hint}{total_credits}{bcolors.ENDC}", end="")
    print("/120 cr.")


if __name__ == "__main__":
    guide = FITCourseGuide("courses.pkl", "specializations.pkl")

    guide.help_me_decide("NVIZ",
                         [["FCE", "FITw"],
                          ["VYF", "PP1", "KNN", "ZPO", "VGE"],
                          ["GZN", "PGR", "POVa", "PCG", "SIN", "VIN"],
                          ["MTIa"]], 0, False)
    # guide.overview_of_specs()

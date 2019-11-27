
import re
import os
import errno
import csv

from datetime import datetime
import time

############### README ################
# Folders for assignments to compile mst be in same directory as script
# Set assignment_name to the full name of the assignment on owl
# Set merge_folders to the names of the subfodlers to merge
# To upload on owl add "grades.csv" and "<assignment_name>" folders to archive
#######################################

assignment_name = "Assignment 1"
merge_folders = ["Bingran", "Nick", "Saby", "Qiang"]

# due date in UTC+0000 timezone
due_date = datetime.strptime("24/01/19 5:00", "%d/%m/%y %H:%M")
full_grade = 90



name_extractor = re.compile(r"([\w|-|\W]+)[,|_]\s([\w+|\s|\W]*)\((\w+)\)")
grade_extractor = re.compile(r"[Q,q]*(\d*)(?:\(*?(\w)\)*)*:\s*([\d.]*)\s*/([\d.]*)([\w|\W]*)")

# Returns hash of student name/westernid
def get_student (filename):
    regex_results = name_extractor.match(filename)
    # only proceed if student sub_dir is correct
    if (regex_results):
        extracted = name_extractor.match(filename).groups()
        return {
            "name_unparsed": filename,
            "lastname": extracted[0],
            "firstname": extracted[1],
            "westernid": extracted[2]
        }
    #else return a invalid flag(0)
    return 0

# Extracts question aswers and returns a hash of answers
def extract_answers (file_in):
    scores = {}
    for line in file_in:
        # Skip blank lines
        if line.strip() == "":
            continue
        extracted = grade_extractor.match(line.strip()).groups()
        scores["{0}{1}".format(extracted[0], ":{0}".format(extracted[1]) if not extracted[1] is None else "")] = {
            "grade": [float(extracted[2]), float(extracted[3])],
            "comment": extracted[4]
        }
    return scores

# Extracts timestamp
def calculate_overdue_days (file_in):
    submit_date = datetime.strptime(file_in.readline(), '%Y%m%d%H%M%S%f')
    # if overdue for less than 5 minutes, count as on time
    if (int(time.mktime(submit_date.timetuple())-time.mktime(due_date.timetuple())) / 60 < 5):
        return -1
    return (submit_date - due_date).days + 1

def calculate_overdue_penalty (days):
    if (days == 1 or days == 2):
        return full_grade * 0.04
    elif (days == 3):
        return full_grade * 0.08
    elif (days == 4):
        return full_grade * 0.16
    return 0

# Combine answers to a single hash
def combine_answers (student_info, packs):
    # only proceed if student sub_dir is correct
    if student_info != 0:
        final_result = student_info
        final_result["answers"] = {}
        for section in packs:
            for question, answer in section.items():
                final_result["answers"][question] = answer
        return final_result
    return 0

# Create one large comments block
def concat_comments (student_result):
    final_comment = ""
    for question_num in sorted([question_key for question_key,v in student_result["answers"].items()]):
        final_comment += "{0} - {1}/{2} {3}\n".format(question_num,
                                                      student_result["answers"][question_num]["grade"][0],
                                                      student_result["answers"][question_num]["grade"][1],
                                                      student_result["answers"][question_num]["comment"])
    return final_comment

# Calculate the final grade of a student
def calculate_grade (student_result):
    total_results = [0,0]
    for question_num, question_result in student_result["answers"].items():
        total_results[0] += question_result["grade"][0]
        total_results[1] += question_result["grade"][1]
    return total_results



final_grades = {}

# Get all the data into the final_grades HASH
tempname = "./{0}/".format(merge_folders[0])
for sub_dir in os.listdir(tempname):
    answer_packs = []
    for marker in merge_folders:
        tempname1 = "./{0}/{1}/comments.txt".format(marker, sub_dir)
        tempname2 = "./{0}/{1}/timestamp.txt".format(marker, sub_dir)
        # check comments file exists to avoid runtime error
        if os.path.isfile(tempname1):
            with open(tempname1, "r") as fin:
                answer_packs.append(extract_answers(fin))
            with open(tempname2, "r") as fin:
                overdue_days = calculate_overdue_days(fin)
            combined_results = combine_answers(get_student(sub_dir), answer_packs)
            final_data = {
                "before": combined_results,
                "comments": concat_comments(combined_results),
                "grade": calculate_grade(combined_results),
                "overdue_days": overdue_days
            }
            final_grades[combined_results["westernid"]] = final_data

# Compile student comments
for student_western, result in final_grades.items():
    folder_name = result["before"]["name_unparsed"].replace("_", ",")
    comments_out = "./compiled/{0}/{1}/comments.txt".format(assignment_name, folder_name)
    # Create the folder
    try:
        os.makedirs(os.path.dirname(comments_out))
    except OSError as exc: # Guard against race condition
        if exc.errno != errno.EEXIST:
            raise
    with open(comments_out, "w") as fout:
        fout.write(result["comments"])
        # add late penalty comments if over due
        if (result["overdue_days"] > 0):
            fout.write("Late penalty: " + str(calculate_overdue_penalty(result["overdue_days"])))
    print(result["overdue_days"])


unfound = []
# Compile student grades
with open("./grades.csv", "r") as csvin:
    with open("./compiled/grades.csv", "w") as csvout:
        # Skip headers
        for _ in range(3):
            newline = csvin.readline()
        # Create csv reader and writer
        blankreader = csv.reader(csvin, delimiter=',', quotechar='"')
        blankwriter = csv.writer(csvout, delimiter=',', quotechar='"', quoting=csv.QUOTE_ALL)
        # Check if student mark was found
        for row in blankreader:
            achieved = 0
            try:
                achieved = final_grades[row[0]]["grade"][0]
            except KeyError as e:
                achieved = 0
                unfound.append(row[0])
            # add late penalty if needed
            if (achieved > 0):
                achieved -= calculate_overdue_penalty(final_grades[row[0]]["overdue_days"])
            # Write row to result
            new_row = row
            new_row[4] = str(achieved)
            blankwriter.writerow(new_row)

print("Found no submission for {0} students:".format(len(unfound)))
for s in unfound:
    print("    {0}".format(s))


import pickle
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report


# SmartCampus complaint training dataset
training_data = {
    "Laboratory Equipment": [
        "Lab computer is not working",
        "Laboratory PC does not start",
        "Computer screen is blank in the lab",
        "Keyboard is damaged in computer lab",
        "Mouse is not working in laboratory",
        "Lab computer keeps restarting",
        "Computer is running very slowly in lab",
        "Laboratory computer has a hardware problem",
        "CPU is not turning on in the lab",
        "Computer monitor is damaged",
        "Printer is not working in computer lab",
        "Lab computer shows a boot error",
        "Computer system needs repair in laboratory",
        "Laboratory PC has no display",
        "Computer keyboard keys are not working",
        "Mouse pointer is not moving in lab",
        "Computer shuts down during practical",
        "Laboratory equipment is damaged",
        "PC is not responding during practical",
        "Computer system in the lab is faulty",
        "Lab workstation is not starting",
        "Computer power button is not working",
        "Laboratory computer has a technical fault",
        "Desktop computer needs maintenance",
    ],

    "Internet / Network": [
        "WiFi is not working in classroom",
        "Internet connection is very slow",
        "Unable to connect to campus WiFi",
        "Network is disconnected in the lab",
        "Internet keeps disconnecting",
        "WiFi signal is weak in college",
        "Campus internet is unavailable",
        "Network connection problem in classroom",
        "Students cannot access the internet",
        "Router is not working",
        "WiFi password is not working",
        "Internet is unavailable in the library",
        "College network connection is unstable",
        "No internet access in computer lab",
        "WiFi keeps dropping during lectures",
        "Network cable connection is faulty",
        "Campus WiFi has poor connectivity",
        "Internet speed is too low",
        "Unable to connect laptop to college WiFi",
        "Network is down in the department",
        "Wireless connection is unavailable",
        "College internet is not responding",
        "WiFi connection fails repeatedly",
        "Internet access is interrupted in hostel",
    ],

    "Classroom Furniture": [
        "Classroom bench is broken",
        "Desk is damaged in classroom",
        "Chair is broken in lecture hall",
        "Students do not have enough benches",
        "Classroom furniture needs repair",
        "Broken table in classroom",
        "Bench is uncomfortable and damaged",
        "Chair is missing from classroom",
        "Desk drawer is damaged",
        "Classroom seating needs repair",
        "Several benches are broken in the classroom",
        "Lecture hall chairs are damaged",
        "Students need additional desks",
        "Classroom table has a broken leg",
        "Wooden bench needs repair",
        "Classroom chairs are unstable",
        "Furniture is damaged in seminar hall",
        "There are not enough seats in class",
        "Desk surface is broken",
        "Bench screws are loose in classroom",
        "Broken chair in the college classroom",
        "Classroom furniture is unsafe to use",
        "Damaged study tables in lecture room",
        "Need repair of classroom benches",
    ],

    "Electricity": [
        "Lights are not working in classroom",
        "Fan is not working",
        "Power supply is unavailable",
        "Electric switch is damaged",
        "Classroom has no electricity",
        "Tube light is broken",
        "Ceiling fan stopped working",
        "Electrical socket is damaged",
        "Power keeps going off",
        "Need repair for classroom lights",
        "Electricity is unavailable in laboratory",
        "Sparks coming from electrical switch",
        "Classroom fan makes noise and stops",
        "Power socket is not working",
        "Lights keep flickering in the classroom",
        "Electrical wiring needs repair",
        "Hostel room has no power supply",
        "Corridor lights are not working",
        "Electric switchboard is broken",
        "Frequent power cuts in the department",
        "Ceiling lights have stopped working",
        "Electric fan regulator is damaged",
        "No power in the seminar hall",
        "Electrical fault in the college building",
    ],

    "Cleanliness": [
        "Washroom is dirty",
        "Classroom is not clean",
        "Dustbins are overflowing",
        "Washroom needs cleaning",
        "Garbage is lying near the classroom",
        "Campus corridor is dirty",
        "Toilet has a bad smell",
        "Waste has not been collected",
        "Classroom floor needs cleaning",
        "Dustbins need to be emptied",
        "Hostel corridor is dirty",
        "College stairs need cleaning",
        "Washroom floor is dirty",
        "Garbage is scattered in the campus",
        "Classroom has not been swept",
        "Dust has accumulated in the library",
        "Dirty washbasin in college washroom",
        "Waste bins are full near the canteen",
        "Campus area needs cleaning",
        "Unclean common area in hostel",
        "Dirty floor in the college corridor",
        "Garbage collection is delayed",
        "College washroom is unhygienic",
        "Cleaning staff has not cleaned the classroom",
    ],

    "Digital Board / Projector": [
        "Digital board is not working",
        "Projector is not turning on in classroom",
        "Smart board display is blank",
        "Projector image is blurry",
        "Digital teaching board is damaged",
        "Classroom projector has no display",
        "Smart board touch is not responding",
        "Projector remote is not working",
        "Digital board screen is frozen",
        "Projector is showing an error",
        "Interactive board is not responding",
        "Projector lamp needs replacement",
        "Smart classroom display is not working",
        "Digital board has a display problem",
        "Projector connection to laptop fails",
        "Classroom smart board has no power",
        "Projector screen is not displaying slides",
        "Touchscreen board needs repair",
        "Seminar hall projector is faulty",
        "Digital classroom equipment is not working",
        "Projector keeps shutting down",
        "Smart board calibration is incorrect",
        "Presentation display is not working",
        "Digital board requires maintenance",
    ],

    "Water Supply / Plumbing": [
        "No water supply in college washroom",
        "Water tap is leaking",
        "Drinking water dispenser is not working",
        "Water cooler is broken",
        "Hostel bathroom tap has no water",
        "Water pipe is leaking in the campus",
        "Washbasin tap is damaged",
        "Water supply is interrupted in hostel",
        "College water cooler needs repair",
        "Water is leaking from the pipe",
        "No drinking water near the classroom",
        "Washroom flush is not working",
        "Water tank is overflowing",
        "Plumbing problem in college building",
        "Tap water pressure is very low",
        "Water dispenser is not cooling",
        "Broken pipe near the hostel",
        "Water supply stopped in the department",
        "Leaking faucet in the washroom",
        "Water cooler tap is damaged",
        "Drain pipe is blocked in washroom",
        "Water is not coming from the tap",
        "Repair the leaking hostel bathroom pipe",
        "Drinking water facility is unavailable",
    ],

    "Road / Footpath Damage": [
        "Road inside campus has potholes",
        "Footpath is broken near the college building",
        "Internal campus road is damaged",
        "Potholes on the road near the library",
        "Broken pathway in the college campus",
        "Campus road surface is uneven",
        "Footpath tiles are broken",
        "Damaged road near the hostel",
        "Internal road needs repair",
        "Pothole near the college parking area",
        "Broken pavement near the canteen",
        "Campus walkway is damaged",
        "Road inside college premises is cracked",
        "Footpath is unsafe near the academic block",
        "Uneven pathway near the laboratory",
        "Repair the damaged hostel access road",
        "Broken tiles on campus footpath",
        "Potholes on the internal college road",
        "College campus walkway needs maintenance",
        "Damaged pavement near the sports ground",
        "Rain has damaged the campus road",
        "Broken pathway near the main college building",
        "Internal campus road has cracks",
        "Footpath repair required inside college",
    ],

    "Food Quality / Hygiene": [
        "Canteen food quality is poor",
        "Food served in mess is cold",
        "Unhygienic food in college canteen",
        "Hostel mess food tastes stale",
        "Food is undercooked in the canteen",
        "Dirty plates in the college mess",
        "Canteen kitchen is not clean",
        "Food served in hostel mess is stale",
        "Poor hygiene in the canteen",
        "Drinking glasses in mess are dirty",
        "Food quality in hostel is unacceptable",
        "Canteen food has an unusual smell",
        "Mess serving area is unhygienic",
        "Food is not fresh in the college canteen",
        "Dirty utensils used for serving food",
        "Insects found near canteen food",
        "College mess needs better food hygiene",
        "Canteen tables are dirty after meals",
        "Poor food storage in hostel mess",
        "Food served to students is cold",
        "Unclean kitchen in the college canteen",
        "Hostel mess utensils need cleaning",
        "Canteen drinking water area is dirty",
        "Food hygiene needs improvement in mess",
    ],

    "Other": [
        "I have a general complaint about college facilities",
        "Please look into an issue in the college",
        "There is another problem on campus",
        "I need help with an unspecified campus issue",
        "College facility requires inspection",
        "Please investigate this campus problem",
        "An issue needs attention from college management",
        "I want to report a general campus concern",
        "Something needs repair in college premises",
        "Please check an unspecified problem in college",
        "A campus facility is causing inconvenience",
        "I have a concern about college services",
        "Please inspect the college premises",
        "An unknown issue needs attention",
        "General maintenance is required on campus",
        "Please review this college complaint",
        "A facility problem needs investigation",
        "I want to report another campus issue",
        "There is a problem with an unspecified facility",
        "College management needs to review this issue",
        "Please help resolve this campus concern",
        "A general issue has been noticed in college",
        "There is an unspecified problem in the department",
        "Please investigate this reported issue",
    ],
}


# Convert category examples into training lists
complaints = []
categories = []

for category, examples in training_data.items():
    complaints.extend(examples)
    categories.extend([category] * len(examples))


print("Total training examples:", len(complaints))
print("Total categories:", len(training_data))

# Keep some data separate for evaluation
X_train, X_test, y_train, y_test = train_test_split(
    complaints,
    categories,
    test_size=0.20,
    random_state=42,
    stratify=categories
)

# TF-IDF + Logistic Regression model
model = Pipeline([
    (
        "tfidf",
        TfidfVectorizer(
            lowercase=True,
            ngram_range=(1, 2),
            strip_accents="unicode",
            sublinear_tf=True
        )
    ),
    (
        "classifier",
        LogisticRegression(
            max_iter=2000,
            class_weight="balanced",
            random_state=42
        )
    )
])

# Train and evaluate
model.fit(X_train, y_train)

predictions = model.predict(X_test)
accuracy = accuracy_score(y_test, predictions)

print("\nSmartCampus AI model trained successfully!")
print(f"Evaluation accuracy: {accuracy:.2%}")
print("\nClassification report:")
print(
    classification_report(
        y_test,
        predictions,
        zero_division=0
    )
)

# Save model beside this script
model_path = Path(__file__).with_name("complaint_model.pkl")

with open(model_path, "wb") as file:
    pickle.dump(model, file)

print(f"\nModel saved successfully: {model_path}")

# Quick sample predictions
test_complaints = [
    "WiFi is not working in AIML lab",
    "The laboratory computer is not starting",
    "Classroom bench is broken",
    "Projector is not working in lecture hall",
    "No water supply in hostel washroom",
    "There are potholes on the internal campus road",
    "Canteen food is stale and unhygienic",
]

print("\nSample predictions:")
for complaint in test_complaints:
    prediction = model.predict([complaint])[0]
    print(f"{complaint} -> {prediction}")

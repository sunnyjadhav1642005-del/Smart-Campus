
import pickle
from pathlib import Path

from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression


# Demo training dataset.
# Labels are example labels, not verified campus incident records.
training_data = [

    # HIGH PRIORITY: Safety risks and major service failures
    ("Electrical sparks from classroom switchboard", "High"),
    ("Burning smell from electrical wiring in lab", "High"),
    ("Major water leakage flooding the computer lab", "High"),
    ("Multiple computers failed during an important examination", "High"),
    ("Broken glass creating a safety hazard in classroom", "High"),
    ("Exposed electrical wires in hostel corridor", "High"),
    ("Severe water pipe burst near campus building", "High"),
    ("Laboratory equipment overheating and smoking", "High"),
    ("Main campus building power wiring is damaged", "High"),
    ("Dangerous pothole at the main internal campus entrance", "High"),
    ("Hostel electrical panel is making sparks", "High"),
    ("Fire alarm is not working in the laboratory", "High"),

    # New examples: complete power failure
    ("Complete power failure in AIML laboratory", "High"),
    ("Complete power failure in the laboratory all computers are switched off", "High"),
    ("Entire computer lab has no electricity students cannot perform practicals", "High"),
    ("Power outage affecting all computers in the AIML lab", "High"),
    ("Electricity supply completely stopped in the computer laboratory", "High"),
    ("No power in the entire laboratory and all practical sessions are stopped", "High"),
    ("Complete electrical failure in the campus computer lab", "High"),
    ("Entire classroom building has lost electricity", "High"),
    ("Major power failure affecting multiple campus laboratories", "High"),
    ("All computers and laboratory equipment stopped due to power failure", "High"),
    ("Electricity outage across the whole academic building", "High"),
    ("Main electrical supply failure affecting students in the lab", "High"),
    ("Complete power outage in hostel building", "High"),
    ("Electrical short circuit in the laboratory", "High"),
    ("Exposed live wire in campus corridor creating a safety risk", "High"),

    # MEDIUM PRIORITY: Localized faults and routine disruptions
    ("WiFi is not working in the AIML laboratory", "Medium"),
    ("Classroom projector is not working", "Medium"),
    ("Several library computers are slow", "Medium"),
    ("Water supply is unavailable in one washroom", "Medium"),
    ("Classroom fan is not working", "Medium"),
    ("Hostel water cooler is not working", "Medium"),
    ("Digital board is not starting in the classroom", "Medium"),
    ("Laboratory computer keyboard is damaged", "Medium"),
    ("Canteen wash basin tap is leaking", "Medium"),
    ("Internal campus footpath tiles are damaged", "Medium"),
    ("Classroom lights are not turning on", "Medium"),
    ("Network connection is frequently disconnecting", "Medium"),
    ("One computer in the AIML lab is not working", "Medium"),
    ("Power socket is not working at one laboratory desk", "Medium"),
    ("Electricity is unavailable in one classroom", "Medium"),
    ("A few lights are not working in the laboratory", "Medium"),
    ("One lab computer keeps restarting", "Medium"),
    ("WiFi signal is weak in one classroom", "Medium"),
    ("Projector power cable is not working", "Medium"),
    ("One floor has intermittent electricity supply", "Medium"),

    # LOW PRIORITY: Minor maintenance issues
    ("Classroom bench needs minor repair", "Low"),
    ("A classroom chair has a loose screw", "Low"),
    ("Notice board needs cleaning", "Low"),
    ("Small paint peeling on classroom wall", "Low"),
    ("One library chair needs adjustment", "Low"),
    ("Minor scratch on a classroom desk", "Low"),
    ("Hostel cupboard handle is loose", "Low"),
    ("A small label is missing from a classroom door", "Low"),
    ("Seminar hall curtain needs minor adjustment", "Low"),
    ("Sports ground signboard needs repainting", "Low"),
    ("Classroom desk has a slightly loose edge", "Low"),
    ("A small section of a wall needs repainting", "Low"),
    ("Classroom bench has a minor scratch", "Low"),
    ("Notice board frame needs cleaning", "Low"),
    ("One chair needs a small adjustment", "Low"),
]

texts = [item[0] for item in training_data]
labels = [item[1] for item in training_data]

priority_model = Pipeline([
    (
        "tfidf",
        TfidfVectorizer(
            lowercase=True,
            ngram_range=(1, 2),
            strip_accents="unicode"
        )
    ),
    (
        "classifier",
        LogisticRegression(
            max_iter=1000,
            class_weight="balanced",
            random_state=42
        )
    )
])

priority_model.fit(texts, labels)

model_path = Path(__file__).with_name("priority_model.pkl")

with open(model_path, "wb") as file:
    pickle.dump(priority_model, file)

print("Priority prediction model trained successfully!")
print("Saved model:", model_path)
print("Priority classes:", list(priority_model.classes_))
print("Training examples:", len(training_data))
print("Note: This is a demo model trained on example data.")

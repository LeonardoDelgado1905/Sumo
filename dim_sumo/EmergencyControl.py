import xml.etree.ElementTree as ET
from utils import mean_confidence_interval

tree = ET.parse('data/out-tripinfo.xml')
root = tree.getroot()

list_emergency_times = []
list_total_times = []
for tripinfo in root:
    if "emergency" in tripinfo.attrib.get("id"):
        list_emergency_times.append(float(tripinfo.attrib.get("waitingTime")))
    list_total_times.append(float(tripinfo.attrib.get("waitingTime")))

if len(list_emergency_times) > 0:
    print("Promedio de tiempo de espera en segundos para los carros de prioridad: ", mean_confidence_interval(list_emergency_times))
print("Promedio de tiempo de espera en segundos para todos los carros: ", mean_confidence_interval(list_total_times))
import xml.etree.ElementTree as ET
from statistics import mean

tree = ET.parse('data/out-tripinfo.xml')
root = tree.getroot()

list_emergency_times = []
list_total_times = []
for tripinfo in root:
    if "emergency" in tripinfo.attrib.get("id"):
        list_emergency_times.append(float(tripinfo.attrib.get("waitingTime")))
    list_total_times.append(float(tripinfo.attrib.get("waitingTime")))

print("Promedio de tiempo de espera en segundos para los carros de prioridad: ", mean(list_emergency_times))
print("Promedio de tiempo de espera en segundos para todos los carros: ", mean(list_total_times))
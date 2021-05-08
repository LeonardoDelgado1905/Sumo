import xml.etree.ElementTree as ET
from statistics import mean

tree = ET.parse('data/out-tripinfo.xml')
root = tree.getroot()

list_times = []
for tripinfo in root:
    if "emergency" in tripinfo.attrib.get("id"):
        list_times.append(float(tripinfo.attrib.get("waitingTime")))

print("Promedio de tiempo de espera en segundos para los carros de prioridad: ", mean(list_times))
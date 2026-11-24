from app.simulation import next_step,next_rule,next_weather_rule,next_mpc,write_routes,WEATHER
import math
import xml.etree.ElementTree as ET

def test_rule_matches_original():
    assert next_rule(100,30)==90
    assert next_rule(80,40)==80
    assert next_rule(90,80)==100
    assert next_rule(70,float('nan'))==70
    assert next_weather_rule(100,50,'dry')==next_rule(100,50)
    assert next_weather_rule(100,80,'heavy_rain')==90

def test_mpc_from_reference():
    obs={'n_up':120,'n_down':60,'arrival_per_min':50,'downstream_speed_kmh':30}
    assert next_mpc(100,obs) in (90,100)

def test_route_writer(tmp_path):
    fn=tmp_path/'route.xml'
    write_routes(fn,2600,'dry',1200)
    rt=ET.parse(fn).getroot()
    assert rt.find('flow').attrib['departLane']=='random'
    assert rt.find('flow').attrib['end']=='1200'
    assert rt.find('vType').attrib['tau']==str(WEATHER['dry']['tau'])

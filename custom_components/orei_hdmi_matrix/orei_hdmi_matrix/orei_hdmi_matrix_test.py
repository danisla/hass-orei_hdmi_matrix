from orei_hdmi_matrix import HDMIMatrixAPI
import time

host = "192.168.1.131"

if __name__ == "__main__":
    api = HDMIMatrixAPI()
    resp = api.get_video_status(host)
    print(resp)
    for field in ["comhead", "allsource", "allinputname", "alloutputname"]:
        assert (
            field in resp
        ), f"Field '{field}' not found in 'get_video_status' response"
    assert "get video status" in resp["comhead"]

    resp = api.get_output_status(host)
    print(resp)
    for field in [
        "comhead",
        "allsource",
        "allscaler",
        "allhdcp",
        "allout",
        "allconnect",
        "allarc",
        "name",
    ]:
        assert (
            field in resp
        ), f"Field '{field}' not found in 'get_output_status' response"
    assert "get output status" in resp["comhead"]

    resp = api.get_input_status(host)
    print(resp)
    for field in ["comhead", "edid", "inactive", "inname", "power"]:
        assert (
            field in resp
        ), f"Field '{field}' not found in 'get_input_status' response"
    assert "get input status" in resp["comhead"]

    # resp = api.video_switch(host, 1, 2)
    # print(resp)
    # for field in ["comhead", "result"]:
    #     assert field in resp, f"Field '{field}' not found in 'video_switch' response"
    # assert "video switch" in resp["comhead"]
    # assert resp["result"] == 1

    resp = api.get_system_status(host)
    initial_state = resp
    if resp["power"] == 1:
        print("initial state was on, changing to standby")
        api.standby(host)
        resp = api.get_system_status(host)
        while resp["power"] != 0:
            resp = api.get_system_status(host)
            print(resp)
            time.sleep(2)
    else:
        print("initial state was standby, changing to power_on")
        api.power_on(host)
        resp = api.get_system_status(host)
        while resp["power"] != 0:
            resp = api.get_system_status(host)
            print(resp)
            time.sleep(2)

    if initial_state["power"] == 1:
        print("returning to power_on")
        api.power_on(host)
    else:
        print("returning to standby")
        api.standby(host)

    print("All tests passed")

Probe Accuracy Testing
======================

This is for testing the accuracy of the toolhead probe on a 3D printer running Klipper.  There are three parts
to this test:

1. a macro to run the test
2. a command line to collect the results
3. a Python script to create a chart from the results

Installation
------------

Create a Python environment for this script.  Use ssh to log in to the Raspberry Pi, and run the following:

    sudo apt install python3-venv
    python3 -m venv /home/pi/plotly-env
    /home/pi/plotly-env/bin/pip install -U plotly
    mkdir /home/pi/probe_accuracy

Download `probe_accuracy.py` from this repository and copy it into `/home/pi/probe_accuracy/` on the Raspberry Pi.

Download `test_probe_accuracy.cfg` from this repository and copy it to the directory containing your
`printer.cfg` - it's `/home/pi/klipper_config/` if you're using MainsailOS.  Edit your `printer.cfg` and add the
following on a new line:

    [include test_probe_accuracy.cfg]

Restart Klipper.

Test Execution
--------------

Home and level your printer (G32 on a VORON 2).  Use ssh to log in to the Raspberry Pi and run the following
to start the data collection:

     while read -r line; do echo `/bin/date +%s`: "$line"; done < /tmp/printer > /tmp/probe_accuracy.txt

**IMPORTANT**:  Leave that ssh session/window open for the duration of the test.

Run the test macro on the printer:

    TEST_PROBE_ACCURACY

It will continuously run `PROBE_ACCURACY` while heating up the bed, soaking the bed, heating up the hotend, and
soaking the hotend.  See below if you want to change the temperatures or soak times.  The default will heat the
bed to 110, soak for 30 minutes, then heat the hotend to 240, and soak for 15 minutes - so this test will
probably take over an hour to run.  Get some coffee while you wait.

After the test is complete, the printer will raise the toolhead a little and turn off the heaters.  Go back
to the ssh session that you were supposed to leave open and press Ctrl+C to stop the data collection.

Parsing Results
---------------

In your Raspberry Pi ssh session run:

    /home/pi/plotly-env/bin/python3 /home/pi/probe_accuracy/probe_accuracy.py

It will save the output file to `/tmp/probe_accuracy.html` .  Copy that file over to your local machine and open
it.  It should contain a chart showing the Z height over time, as the bed and the hotend heat up.

Customizing Time and Temperature
--------------------------------

You can pass parameters to the macro to change the temperatures and soak times:

    TEST_PROBE_ACCURACY [BED_TEMP=<value>] [EXTRUDER_TEMP=<value>] [BED_SOAK_MINUTES=<value>] [EXTRUDER_SOAK_MINUTES=<value>]

The temperatures are in Celsius.  The defaults are as follows:

    TEST_PROBE_ACCURACY BED_TEMP=110 EXTRUDER_TEMP=240 BED_SOAK_MINUTES=30 EXTRUDER_SOAK_MINUTES=15

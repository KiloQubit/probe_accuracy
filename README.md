Probe Accuracy Testing
======================

This is for testing the accuracy of the toolhead probe on a 3D printer running Klipper.  There are two parts
to this test:

1. a macro to run the test
2. a Python script to collect the results and create a chart

Installation
------------

Create a Python environment for this script.  Use ssh to log in to the Raspberry Pi, and run the following:

    sudo apt install python3-venv
    python3 -m venv ~/plotly-env
    ~/plotly-env/bin/pip install -U plotly
    mkdir ~/probe_accuracy

Download `probe_accuracy.py` from this repository and copy it into `~/probe_accuracy/` on the Raspberry Pi:
```bash
cd ~/probe_accuracy
wget -O probe_accuracy.py https://raw.githubusercontent.com/KiloQubit/probe_accuracy/master/probe_accuracy.py
```

Download `test_probe_accuracy.cfg` from this repository and copy it to the directory containing your
`printer.cfg` - it's `~/printer_data/config/` if you're using a current version of 
[MainsailOS](https://github.com/mainsail-crew/MainsailOS):
```bash
cd ~/printer_data/config
wget -O test_probe_accuracy.cfg https://raw.githubusercontent.com/KiloQubit/probe_accuracy/master/test_probe_accuracy.cfg
```

Edit your `printer.cfg` and add the following on a new line:

    [include test_probe_accuracy.cfg]

Restart Klipper.

Test Execution
--------------

Home and level your printer (G32 on a [VORON 2](https://vorondesign.com)).  Position the nozzle over the bed
where you want to test the probe, probably in the center of the bed.  Use ssh to log in to the Raspberry
Pi and run the following to start the data collection:

    ~/plotly-env/bin/python3 ~/probe_accuracy/probe_accuracy.py

> **Warning**
> Leave that ssh session/window open for the duration of the test.

> **Note**
> If you get a `FileNotFoundError`, your Klipper API server socket may be in a different location.
> You can pass a different location to the script using the `--klippy-uds /some/other/location` option

Alternatively, if you don't want to leave the window open, or have a bad network connection to the Pi, you
can run the script in the background, and then you don't have to leave the ssh session open:

    nohup ~/plotly-env/bin/python3 ~/probe_accuracy/probe_accuracy.py >/tmp/probe_accuracy.log 2>&1 &

Run the test macro on the printer:

    TEST_PROBE_ACCURACY

It will continuously run `PROBE_ACCURACY` while heating up the bed, soaking the bed, heating up the hotend, and
soaking the hotend. See below if you want to change the temperatures or soak times.  The default will heat the
bed to 110, soak for 30 minutes, then heat the hotend to 150, and soak for 15 minutes - so this test will
probably take over an hour to run.  Get some coffee while you wait.

After the test is complete, the printer will raise the toolhead a little and turn off the heaters.  The chart
output should be on the Raspberry Pi in `/tmp/probe_accuracy.html` - copy that file to your local machine and
open it.  It should contain a chart showing the Z height over time, as the bed and the hotend heat up.  There's
also a `/tmp/probe_accuracy.json` file generated on the Raspberry Pi, which contains the data used for the chart.
You can download it and use it to create your own chart if you wish.

All thermistors defined in your `printer.cfg` are plotted on the chart.  Once the chart is opened, you can click
on the legend of any thermistor in the chart to turn the trace on or off.

Plotting Existing Data
----------------------

If you already have a JSON data file and want to generate a chart from it, you can use the `--plot-only` option.

    ~/plotly-env/bin/python3 ~/probe_accuracy/probe_accuracy.py \
        --plot-only \
        --data-file /tmp/probe_accuracy.json \
        --chart-file /tmp/probe_accuracy.html

Customizing The Test
--------------------

You can pass parameters to the macro to change the temperatures, soak times and dwell behavior:

    TEST_PROBE_ACCURACY [START_IDLE_MINUTES=<value>]
                        [BED_TEMP=<value>] [EXTRUDER_TEMP=<value>]
                        [BED_SOAK_MINUTES=<value>] [EXTRUDER_SOAK_MINUTES=<value>]
                        [DWELL_SECONDS=<value>] [DWELL_LIFT_Z=<value>]
                        [END_IDLE_MINUTES=<value>]

The temperatures are in Celsius.  The defaults are as follows:

    TEST_PROBE_ACCURACY START_IDLE_MINUTES=5
                        BED_TEMP=110 EXTRUDER_TEMP=150
                        BED_SOAK_MINUTES=30 EXTRUDER_SOAK_MINUTES=15
                        DWELL_SECONDS=1 DWELL_LIFT_Z=-1
                        END_IDLE_MINUTES=10

`START_IDLE_MINUTES` is the amount of time the test will wait at the start before heating up the bed.

Setting `BED_TEMP` or `EXTRUDER_TEMP` to `-1` allows you to disable heating and soaking the bed or
the extruder. Thus you could run a test with just the extruder and without ever turning on the bed.

`DWELL_SECONDS` is the approximate amount of time between running `PROBE_ACCURACY` commands.  If
`DWELL_LIFT_Z` is not `-1`, then the toolhead will be lifted to the specified Z after completing
each `PROBE_ACCURACY`. This is intended to allow the probe to cool away from the bed between probes.

`END_IDLE_MINUTES` is the amount of time the test will wait after turning off the heaters at the end,
while still measuring probe accuracy.

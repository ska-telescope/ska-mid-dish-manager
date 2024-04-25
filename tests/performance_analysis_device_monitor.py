"""Test device Monitor"""
import logging
import random
import statistics
import time
from queue import Empty, Queue
from resource import RUSAGE_SELF, getrusage

import psutil
import tango
from ska_mid_dish_manager.component_managers.device_monitor import TangoDeviceMonitor

LOGGER = logging.getLogger(__name__)


def empty_func(*args, **kwargs):  # pylint: disable=unused-argument
    """An empty function"""
    pass  # pylint:disable=unnecessary-pass


def test_latency(device_fqdn, attributes_to_monitor, test_per_attribute=3):
    """Test that connection is retried"""

    event_queue = Queue()
    tdm = TangoDeviceMonitor(device_fqdn, attributes_to_monitor, event_queue, LOGGER, empty_func)
    tdm.monitor()

    # Wait for setup and clear all the initial updates
    for _ in attributes_to_monitor:
        event_queue.get(timeout=4)

    time_to_respond = {attribute: [] for attribute in attributes_to_monitor}

    device_proxy = tango.DeviceProxy(device_fqdn)

    for attribute in attributes_to_monitor:
        for _ in range(test_per_attribute):
            attribute_value = device_proxy.read_attribute(attribute).value
            write_value = 0 if attribute_value != 0 else 1

            event_queue.queue.clear()

            # print("Queue before:")
            # print([event.item.attr_value.value for event in event_queue.queue])

            # print("Writing value:", write_value)

            start_time = time.time()

            device_proxy.write_attribute(attribute, write_value)

            # Wait for the update to be put onto the queue
            event = event_queue.get(timeout=4)

            end_time = time.time()

            # print("Queue after:")
            # print([event.item.attr_value.value for event in event_queue.queue])

            event_value = event.item.attr_value.value
            # print("Event value:", event_value)
            if event_value != write_value:
                print(f"Event value ({event_value}) does not equal write value ({write_value}).")
                time_to_respond[attribute].append(-1)
                break
            else:
                time_to_respond[attribute].append(end_time - start_time)

            # print(end_time - start_time)

            # Wait for things to settle
            time.sleep(0.2)

    tdm.stop_monitoring()
    return time_to_respond


def test_resource_usage(device_fqdn, attributes_to_monitor):
    """Test that connection is retried"""
    time.sleep(1)
    initial_cpu_usage = psutil.cpu_percent()
    initial_ram_usage = psutil.virtual_memory().percent

    print("(psutil) Initial:")
    print(initial_cpu_usage)
    print(initial_ram_usage)

    print("(resource) Initial:")
    print(getrusage(RUSAGE_SELF))

    event_queue = Queue()
    tdm = TangoDeviceMonitor(device_fqdn, attributes_to_monitor, event_queue, LOGGER, empty_func)

    tdm.monitor()

    # Wait for setup and clear all the initial updates
    for _ in attributes_to_monitor:
        event_queue.get(timeout=4)

    cpu_usage = psutil.cpu_percent()
    ram_usage = psutil.virtual_memory().percent

    print("(psutil) After monitoring started:")
    print(cpu_usage)
    print(ram_usage)

    print("(resource) After monitoring started:")
    print(getrusage(RUSAGE_SELF))

    tdm.stop_monitoring()
    return cpu_usage - initial_cpu_usage, ram_usage - initial_ram_usage


def stress_test(device_fqdn, attributes_to_monitor, test_duration=10):
    """Test that all events are captured"""
    event_queue = Queue()
    tdm = TangoDeviceMonitor(device_fqdn, attributes_to_monitor, event_queue, LOGGER, empty_func)

    tdm.monitor()

    # Wait for setup and clear all the initial updates
    for _ in attributes_to_monitor:
        event_queue.get(timeout=4)

    device_proxy = tango.DeviceProxy(device_fqdn)

    # Capture events during the specified duration
    start_time = time.time()

    expected_updates = 0
    captured_events = 0
    while time.time() - start_time < test_duration:
        try:
            # write to random attributes
            num_writes = random.randint(1, len(attributes_to_monitor))

            for i in range(num_writes):
                attribute_index_to_write = i % len(attributes_to_monitor)
                attribute = attributes_to_monitor[attribute_index_to_write]

                attribute_value = device_proxy.read_attribute(attribute).value
                write_value = 0 if attribute_value != 0 else 1

                device_proxy.write_attribute(attribute, write_value)

                expected_updates += 1

            # make sure those updates happen
            for _ in range(num_writes):
                event_queue.get(timeout=2)
                captured_events += 1
        except Empty:
            print("Did not receive expected event!")

    tdm.stop_monitoring()

    return expected_updates, captured_events


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # device_fqdn = "mid-dish/simulator-spf/ska001"
    device_fqdn = "tango://localhost:45678/mid-dish/simulator-spf/ska001#dbase=no"

    test_attributes = (
        "operatingmode",
        "powerstate",
        "healthstate",
        "bandinfocus",
        "b1capabilitystate",
        "b2capabilitystate",
        "b3capabilitystate",
        "b4capabilitystate",
        "b5acapabilitystate",
        "b5bcapabilitystate",
    )

    def print_metrics(metrics, title, table_width=125):
        def get_padding(word, max_length=25):
            padding = " " * (max_length - len(word))
            return padding

        p = get_padding("attribute")

        print("-" * table_width)
        print(f"Attribute{p} | {title}")
        print("-" * table_width)

        overall_min = 0
        overall_max = 0
        overall_mean = 0
        overall_stdev = 0

        for attribute in metrics:
            latency_sum = 0
            for val in metrics[attribute]:
                latency_sum += val
            latency_sum = latency_sum / len(metrics[attribute])

            padding = get_padding(attribute)

            overall_min += min(metrics[attribute])
            overall_max += max(metrics[attribute])
            overall_mean += latency_sum
            overall_stdev += statistics.stdev(metrics[attribute])

            print(
                f"{attribute}{padding} | (Min={min(metrics[attribute]):.10f}), (Max={max(metrics[attribute]):.10f}), (Mean={latency_sum:.10f}), (Stdev={statistics.stdev(metrics[attribute]):.10f})"
            )

        p = get_padding("Average overall")
        print("-" * table_width)
        print(
            f"Average overall{p} | (Min={overall_min/len(metrics):.10f}), (Max={overall_max/len(metrics):.10f}), (Mean={overall_mean/len(metrics):.10f}), (Stdev={overall_stdev/len(metrics):.10f})"
        )
        print("-" * table_width)

    # latencies_a = test_latency(device_fqdn, test_attributes[:1], test_per_attribute=10)
    # latencies_b = test_latency(device_fqdn, test_attributes[:5], test_per_attribute=10)
    # latencies_c = test_latency(device_fqdn, test_attributes[:10], test_per_attribute=10)

    # print("Latency")
    # print("===============")
    # print(f"Run A ({len(latencies_a)} attribute(s)):")
    # print_metrics(latencies_a, "Latency (ms)")

    # print(f"\nRun B ({len(latencies_b)} attribute(s)):")
    # print_metrics(latencies_b, "Latency (ms)")

    # print(f"\nRun C ({len(latencies_c)} attribute(s)):")
    # print_metrics(latencies_c, "Latency (ms)")

    cpu_usage_a, ram_usage_a = test_resource_usage(device_fqdn, test_attributes[:1])
    cpu_usage_b, ram_usage_b = test_resource_usage(device_fqdn, test_attributes[:5])
    cpu_usage_c, ram_usage_c = test_resource_usage(device_fqdn, test_attributes[:10])

    print("\nResource Usage")
    print("===============")
    print(f"1 Attribute: CPU ({cpu_usage_a}) RAM ({ram_usage_a})")
    print(f"5 Attributes: CPU ({cpu_usage_b}) RAM ({ram_usage_b})")
    print(f"10 Attributes: CPU ({cpu_usage_c}) RAM ({ram_usage_c})")

    # test_duration = 30
    # expected_updates, captured_events = stress_test(device_fqdn, test_attributes, test_duration=test_duration)

    # print("\nStress test")
    # print("===============")
    # print("Duration:", test_duration, "s")
    # print("Attribute writes:", expected_updates)
    # print("Captured events:", captured_events)

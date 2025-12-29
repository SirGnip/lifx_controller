'''
Initial controller for LIFX Strip lights supporting basic functionality
'''
import argparse
import random
import time
import lifxlan
import asyncio


MULTI_ZONE_LIGHTS = (
    ('d0:73:d5:77:29:56', '192.168.1.30'),
    ('d0:73:d5:77:3f:ae', '192.168.1.31')
)


def _setup(discover=True):
    api = lifxlan.LifxLAN()
    if discover:
        print('Discovering lights')
        lights = api.get_lights()
    else:
        print(f'Creating {len(MULTI_ZONE_LIGHTS)} lights from explicit list of IP/MAC')
        lights = [lifxlan.MultiZoneLight(*dat) for dat in MULTI_ZONE_LIGHTS]
    for x in lights:
        print(_device_summary_label(x))
    lights.sort(key=lambda b: b.get_label())
    return api, lights


def _device_summary_label(device):
    return device.get_label() + ' - ' + device.get_product_name() + ' ' + device.get_ip_addr() + ':' + str(device.get_port()) + ' ' + device.get_mac_addr()


def _strip_summary_label(strip) -> str:
    zones = strip.get_color_zones()
    return _device_summary_label(strip) + f' - Number of zones: {len(zones)}'


def reset_white():
    api, lights = _setup()
    strip = [d for d in lights if d.supports_multizone()][0]
    strip.set_power(True)
    strip.set_zone_color(0, 23, lifxlan.COLD_WHITE, apply=True)
    strip.set_power(False)


def reset_dark():
    api, lights = _setup()
    strip = [d for d in lights if d.supports_multizone()][0]
    strip.set_power(True)
    strip.set_zone_color(0, 23, [0, 1000, 500, 3000], apply=True)
    # strip.set_power(False)


def reset_black():
    api, lights = _setup()
    strip = [d for d in lights if d.supports_multizone()][0]
    strip.set_power(True)
    strip.set_zone_color(0, 23, [0, 0, 0, 3000], apply=True)
    # strip.set_power(False)


def set_power(power: bool):
    api, lights = _setup()
    strips = [d for d in lights if d.supports_multizone()]
    for s in strips:
        print(_strip_summary_label(s))
        s.set_power(power)


def cycle():
    api, lights = _setup()
    strip = [d for d in lights if d.supports_multizone()][0]
    strip.set_power(True)
    strip.set_zone_color(0, 23, [0, 65000, 65000, 3000], apply=True)
    time.sleep(1)
    strip.set_zone_color(0, 23, [0, 65000, 10000, 3000], apply=True)
    time.sleep(1)
    strip.set_zone_color(0, 23, [30000, 65000, 10000, 3000], apply=True)
    time.sleep(1)
    strip.set_zone_color(0, 23, [60000, 65000, 10000, 3000], apply=True)
    time.sleep(1)
    strip.set_power(False)


def fade(zone_idx):
    DLY = 0.005
    api, lights = _setup()
    strip = [d for d in lights if d.supports_multizone()][0]
    strip.set_power(True)
    for b in range(0, 65000, 50):
        if b % 5000 == 0:
            print(b)
        strip.set_zone_color(zone_idx, zone_idx, [0, 65000, b, 3000], apply=True, rapid=True)
        time.sleep(DLY)
    for b in range(65000, 0, -50):
        if b % 5000 == 0:
            print(b)
        strip.set_zone_color(zone_idx, zone_idx, [0, 65000, b, 3000], apply=True, rapid=True)
        time.sleep(DLY)


def fade2(zone_idx, color, delay):
    c_dark = color.copy()
    c_bright = color.copy()
    c_dark[2] = 0
    c_bright[2] = 65000
    api, lights = _setup()
    strip = [d for d in lights if d.supports_multizone()][0]
    strip.set_power(True)
    print('zero')
    strip.set_zone_color(zone_idx, zone_idx, c_dark, apply=True)
    # time.sleep(0.05)
    print('start up')
    strip.set_zone_color(zone_idx, zone_idx, c_bright, apply=True, duration=delay * 1000)
    time.sleep(delay)
    print('start down')
    strip.set_zone_color(zone_idx, zone_idx, c_dark, apply=True, duration=delay * 1000)
    time.sleep(delay)
    print('done')


def cycle_zone(zone_idx):
    api, lights = _setup()
    strip = [d for d in lights if d.supports_multizone()][0]
    strip.set_power(True)
    colors = [lifxlan.BLUE, lifxlan.GREEN, lifxlan.RED, lifxlan.YELLOW, lifxlan.WHITE, lifxlan.PURPLE, lifxlan.ORANGE,
              lifxlan.CYAN]
    for c in colors:
        strip.set_zone_color(zone_idx, zone_idx, c, apply=True)
        time.sleep(0.8)
    strip.set_power(False)


def main():
    set_power(False)
    # set_power(True)
    # reset_white()
    # reset_dark()
    # reset_black()
    # cycle()
    # cycle_zone(5)
    # cycle_zone(7)
    # fade(15)
    # fade2(16, lifxlan.BLUE, 3)
    # fade2(5, lifxlan.ORANGE, 2)
    # fade2(12, lifxlan.PURPLE, 4)


async def async_fade(strip, zone_idx, color, iterations, delay):
    c_dark = color.copy()
    c_bright = color.copy()
    c_dark[2] = 0
    c_bright[2] = 65000

    strip.set_zone_color(zone_idx, zone_idx, c_dark, apply=True)

    half_delay = delay / 2
    for i in range(iterations):
        strip.set_zone_color(zone_idx, zone_idx, c_bright, apply=True, duration=half_delay * 1000)
        await asyncio.sleep(half_delay)
        strip.set_zone_color(zone_idx, zone_idx, c_dark, apply=True, duration=half_delay * 1000)
        await asyncio.sleep(half_delay)

async def base_fade(strip, zone_idx, color, delay):
    half_delay = delay / 2

    if color is None:
        await asyncio.sleep(delay)
    else:
        c_dark = color.copy()
        c_bright = color.copy()
        c_dark[2] = 0
        c_bright[2] = 2 ** 16 - 1

        rapid = True
        strip.set_zone_color(zone_idx, zone_idx, c_bright, apply=True, duration=half_delay * 1000, rapid=rapid)
        await asyncio.sleep(half_delay)
        strip.set_zone_color(zone_idx, zone_idx, c_dark, apply=True, duration=half_delay * 1000, rapid=rapid)
        await asyncio.sleep(half_delay)


def light_iterator(count: int | None):
    if count is None:
        while True:
            yield None
    else:
        for i in range(count):
            yield i

async def async_fade_master(strip, zone_idx, colors, iterations, delay):
    for _ in light_iterator(iterations):
        for z in range(24):
            c = random.choice(colors)
            delay = random.uniform(2, 5)
            await base_fade(strip, z, c, delay)


async def async_main():
    api, lights = _setup()
    strip = [d for d in lights if d.supports_multizone()][0]
    strip.set_power(True)
    rainbow = [lifxlan.RED, lifxlan.ORANGE, lifxlan.YELLOW, lifxlan.GREEN, lifxlan.BLUE, lifxlan.PURPLE]
    # tasks = [asyncio.create_task(async_fade(strip, idx, random.choice(rainbow), 9, random.uniform(2, 4))) for idx in range(24)]
    cool = [lifxlan.WHITE, lifxlan.WHITE, lifxlan.WHITE, lifxlan.WHITE, lifxlan.BLUE]
    tasks = [asyncio.create_task(async_fade(strip, idx, random.choice(cool), 5, random.uniform(5, 7))) for idx in range(24)]
    await asyncio.gather(*tasks)
    print('done')
    strip.set_power(False)

async def async_zone_fader(strip, zone_idx, iterations, delay_min, delay_max, colors):
    for _ in light_iterator(iterations):
        color = random.choice(colors)
        delay = random.uniform(delay_min, delay_max)
        await base_fade(strip, zone_idx, color, delay)

async def async_main2():
    api, lights = _setup()
    strip = [d for d in lights if d.supports_multizone()][0]
    strip.set_power(True)
    tasks = [asyncio.create_task(async_zone_fader(strip, idx, 5)) for idx in range(24)]
    print(f'created {len(tasks)} tasks')
    await asyncio.gather(*tasks)
    print('done')
    strip.set_power(False)


async def async_main_both(discover, iterations, fade_min, fade_max, colors):
    # Convert 'none' strings to None
    colors = [None if c.lower() == 'none' else c for c in colors]

    # logging
    print(f'Starting with {len(colors)} colors: {[c for c in colors]}')
    print(f'Fade duration: {fade_min}-{fade_max} seconds')
    print(f'Iterations: {iterations if iterations is not None else "infinite"}')

    # Convert colors to LIFX color names. If they don't have a match, this will explicitly fail.
    colors = [None if c is None else getattr(lifxlan, c.upper()) for c in colors]

    # Setup LIFX API
    api, lights = _setup(discover=discover)
    strips = [d for d in lights if d.supports_multizone()]
    print(f'Found {len(strips)} strips')

    # Schedule tasks to control fades (one async task controls each LIFX zone on each string of lights)
    try:
        all_tasks = []
        for strip in strips:
            all_zones = strip.get_color_zones()
            print(_strip_summary_label(strip))
            strip.set_power(True)
            tasks = [asyncio.create_task(async_zone_fader(strip, idx, iterations, fade_min, fade_max, colors))
                    for idx in range(len(all_zones))]
            print(f'Created {len(tasks)} tasks for {strip.get_label()}')
            all_tasks += tasks
        
        await asyncio.gather(*all_tasks)
    except Exception as e:
        print('Got error:', e)
    finally:
        print('Had an expected exit or an error. Powering off lights.')
        for strip in strips:
            strip.set_power(False)

    print('Done')


def parse_args():
    parser = argparse.ArgumentParser(description='Control LIFX Strip lights with various effects')
    parser.add_argument('--discover', action='store_true', default=False,
                      help='Discover lights on the network (default: use pre-configured list)')
    parser.add_argument('--iterations', type=int, default=2,
                      help='Number of iterations to run (default: run forever)')
    parser.add_argument('--fade-min', type=float, default=2.0,
                      help='Minimum fade duration in seconds (default: 2.0)')
    parser.add_argument('--fade-max', type=float, default=4.0,
                      help='Maximum fade duration in seconds (default: 4.0)')
    parser.add_argument('colors', nargs='*', default=['red'],
                      help='List of color names to use (e.g., "red blue yellow none")')
    return parser.parse_args()


if __name__ == '__main__':
    # main()
    # asyncio.run(async_main())
    # asyncio.run(async_main2())
    # asyncio.run(async_main_both())

    # Command line interface
    args = parse_args()
    print(args)
    asyncio.run(async_main_both(
        discover=args.discover,
        iterations=args.iterations,
        fade_min=args.fade_min,
        fade_max=args.fade_max,
        colors=args.colors
    ))

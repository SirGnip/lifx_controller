'''
Initial controller for LIFX Strip lights supporting basic functionality
'''
import argparse
import datetime
import random
import lifxlan
import asyncio
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s.%(msecs)03d %(levelname)s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

RESTART_DELAY = 20
STRIP_COUNT_POLLING_DELAY = 2 * 60  # 2 minutes
MULTI_ZONE_LIGHTS = (
    ('d0:73:d5:77:29:56', '192.168.1.30'),
    ('d0:73:d5:77:3f:ae', '192.168.1.31')
)


async def async_retry(func, *func_args, max_retries=3, delay=0.1, **func_kwargs):
    """Retry a standard function on failure with an async loop.
    
    Args:
        func: The async function to retry
        *func_args: Positional arguments to pass to the function
        max_retries: Maximum number of retry attempts (default: 3)
        delay: Initial delay between retries in seconds (default: 0.1)
        **func_kwargs: Keyword arguments to pass to the function
        
    Returns:
        The result of the function if successful
        
    Raises:
        Exception: The last exception if all retries fail
    """
    last_exception = None
    for attempt in range(max_retries + 1):  # +1 for the initial attempt
        try:
            return func(*func_args, **func_kwargs)
        except Exception as e:
            logging.info(f'ERROR with RETRY: {attempt + 1}/{max_retries} {type(e)} {e}')
            last_exception = e
            if attempt < max_retries:
                await asyncio.sleep((attempt + 1) * delay)  # increase delay time with each retry
    
    # If we get here, all retries failed
    logging.info('ERROR. Exhausted retries. Allowing exception to propagate.')
    raise last_exception


def dump():
    api, lights = _setup()
    for x in lights:
        print(x)


def _setup(discover=True):
    api = lifxlan.LifxLAN()
    if discover:
        logging.info('Discovering lights')
        lights = api.get_lights()
    else:
        logging.info(f'Creating {len(MULTI_ZONE_LIGHTS)} lights from explicit list of IP/MAC')
        lights = [lifxlan.MultiZoneLight(*dat) for dat in MULTI_ZONE_LIGHTS]
    for x in lights:
        logging.info(_device_summary_label(x))
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


async def base_fade(strip, zone_idx, color, delay):
    half_delay = delay / 2

    if color is None:
        await asyncio.sleep(delay)
    else:
        c_dark = color.copy()
        c_dark[2] = 0

        rapid = False
        await async_retry(strip.set_zone_color, zone_idx, zone_idx, color, apply=True, duration=half_delay * 1000, rapid=rapid)
        await asyncio.sleep(half_delay)
        await async_retry(strip.set_zone_color, zone_idx, zone_idx, c_dark, apply=True, duration=half_delay * 1000, rapid=rapid)
        await asyncio.sleep(half_delay)


def light_iterator(count: int | None):
    if count is None:
        while True:
            yield None
    else:
        for i in range(count):
            yield i


async def async_zone_fader(strip, zone_idx, iterations, delay_min, delay_max, colors):
    for _ in light_iterator(iterations):
        color = random.choice(colors)
        delay = random.uniform(delay_min, delay_max)
        await base_fade(strip, zone_idx, color, delay)


def _parse_color(color):
    '''Convert None, LIFX color names, or strings containing 4-tuples into 4-tuples of ints.

    If there isn't a match, explicitly fail.'''
    if color.upper() == 'NONE':
        return None
    try:
        return getattr(lifxlan, color.upper())
    except:
        # Parse 4-tuples (ex: '0,65000,65000,3500')
        vals = [int(x.strip()) for x in color.split(',')]
        return vals


async def strip_count_watcher(api):
    '''Poll the LIFX API to see how many multizone light strips there are. Throw exception if a change is detected.'''
    try:
        count = None
        while True:
            await asyncio.sleep(STRIP_COUNT_POLLING_DELAY)
            tasks = [t for t in asyncio.all_tasks() if not t.done()]

            lights = api.get_lights()
            strips = [d for d in lights if d.supports_multizone()]
            new_count = len(strips)
            logging.info(f"WATCHER: Checking light counts: {new_count} with {len(tasks)} tasks")
            if count is None:
                count = new_count
            else:
                if count != new_count:
                    msg = f"WATCHER: Triggered restart. A change was detected in number of lights from {count} to {new_count}"
                    logging.warning(msg)
                    raise Exception(msg)
    except Exception as e:
        logging.error(str(e))
        raise


async def async_main(discover, iterations, fade_min, fade_max, colors):
    # logging
    logging.info(f'Starting with {len(colors)} colors: {[c for c in colors]}')
    logging.info(f'Fade duration: {fade_min}-{fade_max} seconds')
    logging.info(f'Iterations: {iterations} {"(infinite)" if iterations is None else ""}')

    # Parse input into the list of 4-tuples that LIFX expects
    colors = [_parse_color(c) for c in colors]
    for c in colors:
        logging.info(f'  Color: {c}')

    while True:
        logging.info('-------------------- Startup...')

        # Setup LIFX API
        api, lights = _setup(discover=discover)
        strips = [d for d in lights if d.supports_multizone()]
        # strips = [d for d in strips if d.get_mac_addr() == MULTI_ZONE_LIGHTS[1][0]]  # DEBUGGING - use one strip
        logging.info(f'Found {len(strips)} strips')

        # Schedule tasks to control fades (one async task controls each LIFX zone on each string of lights)
        try:
            all_tasks = []
            for strip in strips:
                all_zones = strip.get_color_zones()
                logging.info(_strip_summary_label(strip))
                strip.set_power(True)
                tasks = [asyncio.create_task(async_zone_fader(strip, idx, iterations, fade_min, fade_max, colors))
                         for idx in range(len(all_zones))]
                logging.info(f'Created {len(tasks)} tasks for {strip.get_label()}')
                all_tasks += tasks

            all_tasks.append(asyncio.create_task(strip_count_watcher(api)))
            await asyncio.gather(*all_tasks)
        except Exception as e:
            logging.info(f'TOP LEVEL ERROR {type(e)} {e}')

        if iterations is not None:
            logging.info('Requested iterations are complete. Exiting.')
            break

        for t in all_tasks:
            logging.info(f"Querying task state: {t}")
            if not t.done():
                logging.info(f"Cancelling task: {t}")
                success = t.cancel()
                logging.info(f"Cancellation {success} for {t}")

        await asyncio.sleep(1.0)
        tasks = [t for t in asyncio.all_tasks() if not t.done()]
        logging.info(f'There are {len(tasks)} remaining that are not Done')
        logging.info(f'Sleeping for {RESTART_DELAY} seconds before full restart...')
        await asyncio.sleep(RESTART_DELAY)
        tasks = [t for t in asyncio.all_tasks() if not t.done()]
        logging.info(f'There are {len(tasks)} remaining that are not Done')

    logging.info('App is exiting')


def parse_args():
    parser = argparse.ArgumentParser(description='Control LIFX Strip lights with various effects')
    parser.add_argument('--discover', action='store_true', default=False,
                      help='Discover lights on the network (default: use pre-configured list)')
    parser.add_argument('--iterations', type=int, default=None,
                      help='Number of iterations to run (default: run forever)')
    parser.add_argument('--fade-min', type=float, default=2.0,
                      help='Minimum fade duration in seconds (default: 2.0)')
    parser.add_argument('--fade-max', type=float, default=4.0,
                      help='Maximum fade duration in seconds (default: 4.0)')
    parser.add_argument('colors', nargs='*', default=['red'],
                      help='List of color names to use (e.g., "red blue yellow none")')
    return parser.parse_args()

def cmd():
    """Simple command-line interface for controlling LIFX lights.
    
    Commands:
      on                 - Turn on all lights
      off                - Turn off all lights
      color COLOR        - Set all zones to COLOR (e.g., 'red', 'blue', '0,65535,65535,3500')
      color ZONE COLOR   - Set specific ZONE to COLOR
      brightness VALUE   - Set brightness (0-100, e.g., 'brightness 50' for 50%)
      quit               - Exit the program
    """
    
    def logg(msg):
        now = datetime.datetime.now()
        print(f'{now.strftime("%Y-%m-%d %H:%M:%S")}.{now.microsecond:06d} {msg}')

    duration = 200  # ms

    # Initialize lights
    logg("Initializing LIFX lights...")
    try:
        api, lights = _setup(discover=True)
        strips = [d for d in lights if d.supports_multizone()]
        if not strips:
            print("No multi-zone LIFX devices found!")
            return

        # List available strips
        print("\nFound strip lights:")
        for i, strip in enumerate(strips, 1):
            print(f"[{i}] {strip.get_label()} - {strip.get_mac_addr()} - {strip.get_ip_addr()}")

        # Let user select a strip
        while True:
            try:
                selection = input("\nSelect strip number (or Enter for first): ").strip()
                if not selection:
                    strip = strips[0]
                    break

                idx = int(selection) - 1
                if 0 <= idx < len(strips):
                    strip = strips[idx]
                    break
                print(f"Please enter a number between 1 and {len(strips)}")
            except ValueError:
                print("Please enter a valid number")

        logg(f"Controlling strip: {strip.get_label()} ({strip.get_mac_addr()}) at {strip.get_ip_addr()}")

        while True:
            try:
                cmd = input("> ").strip()
                if not cmd:
                    continue
                    
                parts = cmd.lower().split()
                command = parts[0]
                
                if command == 'quit':
                    logg("Exiting...")
                    break
                    
                elif command == 'on':
                    strip.set_power(True)
                    logg("Turned lights ON")
                    
                elif command == 'off':
                    strip.set_power(False)
                    logg("Turned lights OFF")
                    
                elif command == 'bright':
                    if len(parts) != 2:
                        print("Usage: bright VALUE (0-100)")
                        continue
                    try:
                        percent = int(parts[1])
                        if not 0 <= percent <= 100:
                            print("Brightness must be between 0 and 100")
                            continue
                        brightness = int((percent / 100) * 65535)
                        logg(f"Set brightness to {percent}% ({brightness}/65535)")
                        strip.set_brightness(brightness, duration=duration)
                    except ValueError:
                        print("Invalid brightness value. Please use a number between 0 and 100")
                
                elif command == 'color':
                    if len(parts) < 2:
                        print("Usage: color COLOR or color ZONE COLOR")
                        continue
                        
                    # Handle 'color ZONE COLOR' format
                    if len(parts) >= 3 and parts[1].isdigit():
                        zone = int(parts[1])
                        try:
                            color_str = ' '.join(parts[2:])
                            color = _parse_color(color_str)
                            strip.set_zone_color(zone, zone, color, apply=True, duration=duration)
                            logg(f"Set zone {zone} to {color_str}")
                        except Exception as e:
                            print(f"Error setting zone color: {e}")
                    # Handle 'color COLOR' format
                    else:
                        try:
                            color_str = ' '.join(parts[1:])
                            color = _parse_color(color_str)
                            strip.set_color(color, duration=duration)
                            logg(f"Set all zones to {color_str}")
                        except Exception as e:
                            print(f"Error setting color: {e}")
                            print("Valid colors: red, blue, green, etc. or HSBK values like '0,65535,65535,3500'")
                    
                else:
                    print("Unknown command. Available commands: on, off, color, quit")
                    
            except KeyboardInterrupt:
                print("\nUse 'quit' to exit")
            except Exception as e:
                print(f"Error: {e}")
                
    except Exception as e:
        print(f"Failed to initialize LIFX: {e}")


if __name__ == '__main__':
    # cmd()  # run command line interface
    # dump()
    # set_power(False)
    # set_power(True)
    # reset_white()
    # reset_dark()
    # reset_black()

    args = parse_args()
    logging.info(f'Command line args: {args}')
    asyncio.run(async_main(
        discover=args.discover,
        iterations=args.iterations,
        fade_min=args.fade_min,
        fade_max=args.fade_max,
        colors=args.colors
    ))

# Puny Domain Check v1.0
# Author: Anil YUKSEL, Mustafa Mert KARATAS
# E-mail: anil [ . ] yksel [ @ ] gmail [ . ] com, mmkaratas92 [ @ ] gmail [ . ] com
# URL: https://github.com/anilyuk/punydomaincheck

import os
from sys import stdout, platform
from core.logger import LOG_HEADER

MISC_DIR = os.path.dirname(os.path.abspath(__file__)) + "/../misc/"
VERSION = "1.0.4"
CONFUSABLE_URL = "http://www.unicode.org/Public/security/latest/confusables.txt"
CONFUSABLE_FILE = MISC_DIR + "confusables.txt"
BLACKLIST_LETTERS = MISC_DIR + "blacklist_letters.json"
WHITELIST_LETTERS = MISC_DIR + "whitelist_letters.json"
CHARSET_FILE = MISC_DIR + "charset.json"
LETTERS_FILE = MISC_DIR + "letters.json"
MAX_THREAD_COUNT = 7
OUTPUT_DIR = "./output"
GEOLOCATION_WEBSITE = "http://freegeoip.net/json"
TIMEOUT = 5
SOCKET_TIMEOUT_SECONDS = 1
### YOUR VIRUSTOTAL API KEYs
VT_APIKEY_LIST = []


BANNER = ''' _ __  _   _ _ __  _   _  ___| |__   ___  ___| | __
| '_ \| | | | '_ \| | | |/ __| '_ \ / _ \/ __| |/ /
| |_) | |_| | | | | |_| | (__| | | |  __/ (__|   <
| .__/ \__,_|_| |_|\__, |\___|_| |_|\___|\___|_|\_\\
|_|                |___/                                {}
'''.format(VERSION)


# Set console colors
if platform != 'win32' and stdout.isatty():
    YEL = '\x1b[33m'
    MAG = '\x1b[35m'
    BLU = '\x1b[34m'
    GRE = '\x1b[32m'
    RED = '\x1b[31m'
    RST = '\x1b[39m'
    CYA = '\x1b[36m'


else:
    YEL = ''
    MAG = ''
    GRE = ''
    RED = ''
    BLU = ''
    CYA = ''
    RST = ''


def alternative_filename(args, output_dir):
    return "{}/{}_{}char_alternatives".format(output_dir, args.domain, args.count)


def print_percentage(args, logger, current, total=0, last_percentage=0, header_print=False):
    if total != 0:
        percentage = int((100 * current) / total)
    else:
        percentage = current

    if not header_print and not args.debug and args.verbose:
        stdout.write("{}Processing: {}0%".format(LOG_HEADER, BLU))
        header_print = True
        stdout.flush()

    if percentage % 10 == 0 and last_percentage != percentage and percentage != 0 and args.verbose:

        last_percentage = percentage
        if args.debug and args.verbose:

            logger.info("[*] Processing... {}{}{}".format(BLU, percentage, RST))

        else:

            if percentage == 100:

                string_stdout = "...{}%{}\n".format(percentage, RST)

            else:

                string_stdout = "...{}%".format(percentage)

            stdout.write(string_stdout)

            stdout.flush()

    return last_percentage, header_print

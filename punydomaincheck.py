#!/usr/bin/python2.7
# Puny Domain Check v1.0
# Author: Anil YUKSEL, Mustafa Mert KARATAS
# E-mail: anil [ . ] yksel [ @ ] gmail [ . ] com, mmkaratas92 [ @ ] gmail [ . ] com
# URL: https://github.com/anilyuk/punydomaincheck

from argparse import ArgumentParser, RawTextHelpFormatter
from sys import exit

from core.creator import *
from core.exceptions import CharSetException, AlternativesExists
from core.logger import start_logger
from core.confusable import update_charset
from core.domain import load_domainnames, dns_client
from core.common import print_percentage, OUTPUT_DIR, BANNER, BLU, RST, RED, GRE, VT_APIKEY_LIST
from core.phishingtest import makeRequest, addProtocol
from time import sleep
from Queue import Queue
from os.path import getsize
from tabulate import tabulate
from os import remove, mkdir, stat

if VT_APIKEY_LIST:
    from core.vt_scan import vt_report_key_positives, vt_report_total, vt_report_key_subdomains


def arg_parser():
    parser = ArgumentParser(formatter_class=RawTextHelpFormatter)
    parser.add_argument("-u", "--update", action="store_true", default=False, help="Update character set")
    parser.add_argument("--debug", action="store_true", default=False, help="Enable debug logging")
    parser.add_argument("-d", "--domain", default=None, help="Domain without prefix and suffix. (google)")
    parser.add_argument("-s", "--suffix", default=None, help="Suffix to check alternative domain names. (com, net, etc)")
    parser.add_argument("-c", "--count", default=1, help="Character count to change with punycode alternative (Default: 1)")
    parser.add_argument("-os", "--original_suffix", default=None,
                        help="Original domain to check for phisihing\n"
                        "Optional, use it with original port to run phishing test")
    parser.add_argument("-op", "--original_port", default=None, help="Original port to check for phisihing\n"
                                                                   "Optional, use it with original suffix to run phishing test")
    parser.add_argument("-f", "--force", action="store_true", default=False,
                        help="Force to calculate alternative domain names")
    parser.add_argument("-t", "--thread", default=15, help="Thread count")
    parser.add_argument("-v", "--verbose", action="store_true", default=False, help="Be verbose")

    return parser.parse_args()


def punyDomainCheck(args, logger):
    letters_json = load_letters()

    try:

        charset_json = load_charset()

    except CharSetException:

        if (not args.update):
            update_charset(logger, letters_json)
            charset_json = load_charset()

    if not args.update and not args.domain:

        logger.info("[-] Use the -h option for help.")
        
        exit()

    elif args.update:

        update_charset(logger, letters_json)

    elif int(args.count) <= len(args.domain):

        if args.original_port and not args.original_suffix:

            logger.info("[-] Original suffix required!")
            exit()

        elif not args.original_port and args.original_suffix:

            logger.info("[-] Original port required!")
            exit()

        if not args.domain:
            logger.info("[-] Domain name required!")
            exit()

        if not args.suffix:
            logger.info("[-] Domain Suffix required!")
            exit()

        if args.original_suffix:
            original_domain = "{}.{}".format(args.domain, args.original_suffix)
            original_url = addProtocol(original_domain, args.original_port)
            if not makeRequest(original_url, logger):
                logger.critical("[-] Original URL doesn't work: \"{}\".".format(original_url))
                exit()

        try:

            stat(OUTPUT_DIR)

        except:

            mkdir(OUTPUT_DIR)

        output_dir = "{}/{}".format(OUTPUT_DIR, args.domain)

        try:

            stat(output_dir)

        except:

            mkdir(output_dir)

        try:

            create_alternatives(args=args, charset_json=charset_json, logger=logger, output_dir=output_dir)

        except AlternativesExists:
            if args.verbose:
                logger.info("[*] Alternatives already created. Skipping to next phase..")
        except NoAlternativesFound:
            logger.info("[*] No alternatives found for domain \"{}\".".format(args.domain))
            exit()
        except KeyboardInterrupt:
            exit()

        domain_name_list = load_domainnames(args=args, output_dir=output_dir)
        dns_thread_list = []
        threads_queue = []
        thread_count = 0
        if args.verbose:
            logger.info("[*] Every thread will resolve {}{}{} names".format(BLU, str(len(domain_name_list[0])), RST))
        # logger.info("[*] {}".format(datetime.now()))

        for list in domain_name_list:

            if len(list) > 0:
                thread_queue = Queue()
                threads_queue.append(thread_queue)

                dns_thread = dns_client(args=args, logger=logger, domain_list=list, output_queue=thread_queue,
                                        thread_name=str(thread_count))
                dns_thread.daemon = True
                dns_thread.start()
                dns_thread_list.append(dns_thread)

                thread_count += 1

        if args.verbose:
            logger.info("[*] DNS Client thread started. Thread count: {}{}{}".format(BLU, len(dns_thread_list), RST))

        dns_client_completed = False
        query_result = []

        last_percentage = 1
        header_print = False

        while not dns_client_completed:

            try:
                sleep(0.001)
            except KeyboardInterrupt:
                print RST
                exit()

            total_percentage = 0

            for dns_thread in dns_thread_list:
                total_percentage += dns_thread.get_percentage()

            total_percentage = total_percentage / int(thread_count)

            last_percentage, header_print = print_percentage(args, logger, total_percentage,
                                                             last_percentage=last_percentage,
                                                             header_print=header_print)

            for queue in threads_queue:
                try:

                    if not queue.empty():
                        query_result.append(queue.get())
                except KeyboardInterrupt:
                    print RST
                    exit()

            if len(query_result) == int(thread_count):
                dns_client_completed = True

        dns_file_name = "{}/{}_dns".format(output_dir, args.domain)
        dns_file_content = []
        dns_file_new_created = True
        try:
            with open(dns_file_name, "r") as file:
                dns_file_content = file.readlines()

        except:
            pass

        else:
            dns_file_new_created = False

        print_header = True

        headers_list = ["","Domain Name", "IP Address", "Whois Name", "Whois Organization", "Whois Email",
                        "Whois Updated Date", "HTTP Similarity", "HTTPS Similarity",
                        "Country", "City", "Virustotal Result", "Subdomains",""]

        dns_file = open(dns_file_name, 'a')
        string_array = []

        for results in query_result:

            for result in results:

                if len(result.get_domain_name()) > 1:

                    whois_email = ""
                    whois_name = ""
                    whois_organization = ""
                    whois_creation_date = ""
                    whois_updated_date = ""
                    whois_result = result.get_whois_result()

                    if whois_result:

                        if "contacts" in whois_result:

                            whois_contacts = whois_result["contacts"]

                            if "admin" in whois_contacts:

                                whois_admin = whois_contacts["admin"]

                                if whois_admin:

                                    if "email" in whois_admin: whois_email = whois_admin["email"]

                                    if "name" in whois_admin: whois_name = whois_admin["name"]

                                    if "organization" in whois_admin: whois_organization = whois_admin["organization"]

                        if "updated_date" in whois_result: whois_updated_date = whois_result["updated_date"][0]

                    if print_header:

                        header_string = ";".join(headers_list[1:-1])

                        if dns_file_new_created:
                            dns_file.write("{}\n".format(header_string))
                        print_header = False

                    http_similarity = ""
                    https_similarity = ""
                    if "http_similarity" in result.get_similarity():
                        http_similarity = result.get_similarity()["http_similarity"]
                    if "https_similarity" in result.get_similarity():
                        https_similarity = result.get_similarity()["https_similarity"]

                    virustotal_result = ""
                    subdomains = ""

                    if result.get_vt_result():
                        virustotal_result = "{}/{}".format(
                            result.get_vt_result()[vt_report_key_positives], result.get_vt_result()[vt_report_total])
                        if vt_report_key_subdomains in result.get_vt_result():
                            subdomains = ",".join(result.get_vt_result()[vt_report_key_subdomains])

                    string_to_write = "{};{};{};{};{};{};{};{};{};{};{};{};{}".format(
                        result.get_domain_name(),
                        result.get_ipaddress(),
                        whois_name,
                        whois_organization,
                        whois_email,
                        whois_creation_date,
                        whois_updated_date,
                        http_similarity,
                        https_similarity,
                        result.get_geolocation()[
                            "country_name"],
                        result.get_geolocation()[
                            "city"],
                        virustotal_result,
                        subdomains)
                    color = ""
                    if "{}\n".format(string_to_write) not in dns_file_content:
                        dns_file.write("{}\n".format(string_to_write))
                        color = RED

                    string_array.append(
                        [color, result.get_domain_name(),
                         result.get_ipaddress(),
                         whois_name,
                         whois_organization,
                         whois_email,
                         whois_updated_date,
                         http_similarity,
                         https_similarity,
                         result.get_geolocation()[
                             "country_name"],
                         result.get_geolocation()[
                             "city"],
                         virustotal_result,
                         subdomains, RST])
        if string_array:
            logger.info(
            "[+] Punycheck result for {}{}.{}{}:\n {}".format(GRE, args.domain, args.suffix, RST,
                                                              tabulate(string_array, headers=headers_list)))
        dns_file.close()

        if getsize(dns_file_name) == 0:
            remove(dns_file_name)

            # logger.info("[*] {}".format(datetime.now()))


charset_json = None

if __name__ == '__main__':
    args = arg_parser()
    if args.verbose:
        print '%s%s%s' % (BLU, BANNER, RST)
    logger = start_logger(args)
    punyDomainCheck(args, logger)

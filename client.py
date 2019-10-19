#!/usr/bin/env python

import time
import sys
import socket
import random
import json
import urllib


class Timer(object):

    def __init__(self):
        self.min_ping = 0
        self.max_ping = 999999
        self.attempted_count = 0
        self.count = 0
        self.avg_time = 0

    def attempt(self):
        self.attempted_count += 1

    def log(self, elapsed):
        if elapsed < self.min_ping:
            self.min_ping = elapsed
        if elapsed > self.max_ping:
            self.max_ping = elapsed
        self.count += 1
        self.avg_time += elapsed

    def update_server(self, client_id, print_out=False):
        stop = False
        if print_out:
            print('--- client response time statistics ---')
            print('rtt min/avg/max/n = {0:.3f}/{1:.3f}/{2:.3f}/{3} ms'.format(
                self.min_ping, self.avg_time / self.count, self.max_ping, self.count
            ))

        if self.client_id is not None:
            data = {
                'client_id': self.client_id,
                'ping_min': self.min_ping,
                'ping_avg': self.avg_time / self.count,
                'ping_max': self.max_ping,
                'ping_count': self.count,
                'ping_misses': self.attemped_count - self.count,
            }
            req = urllib.request('https://www.rileyevans.co.uk/gp/add-result/')
            res = urllib.urlopen(req, json.dumps(data))

            res_data = json.loads(res.read())
            if not res_data['error']:
                stop = res_data['stop']

        return stop


def time_it(f):
    def wrapped_f(timer, *args):
        start = time.time()
        timer.attempt()
        x = f(*args)
        end = time.time()
        elapsed = (end - start) * 1000
        timer.log(elapsed)
        return x
    return wrapped_f


class Game(object):
    def __init__(self, server_ip, interval):
        self.server_ip = server_ip
        self.port = 25565
        self.interval = interval
        self.player_id = None
        self.me = {'x': 0, 'y': 0}
        self.other_players = {}
        self.timer = Timer()
        self.clientSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.clientSocket.settimeout(2)
        self.timeout_count = 0

    def start(self):
        self.handshake()

        self.stop = False

        timer_updates = 20.0 / self.interval

        count = 0

        while not self.stop:
            try:
                self.move()
                self.send_location()
                time.sleep(self.interval)
            except KeyboardInterrupt:
                break
            finally:
                if count > timer_updates:
                    self.stop = self.timer.update_server(self.player_id)

        self.timer.update_server(self.player_id)

    def handshake(self):
        agreed = False
        player_id = None
        while not agreed:
            try:
                player_id = random.randint(1, 255)
                message = bytearray([1, player_id])
                self.clientSocket.sendto(message, (self.server_ip, self.port))
                data, server = receive(self.timer, self.clientSocket)

                if data[0] == 2 and data[1] == player_id:
                    agreed = True
                else:
                    if data[0] != 2:
                        print('unexpected handshake ? {}'.format(data))
                    else:
                        print('client id already taken, trying again')

            except socket.timeout:
                pass
        self.player_id = player_id

    def move(self):
        self.me['x'] += random.randint(0, 2)
        if self.me['x'] > 255:
            self.me['x'] -= 255
        self.me['y'] += random.randint(0, 2)
        if self.me['y'] > 255:
            self.me['y'] -= 255

    def send_location(self):
        message = bytearray([3, self.player_id, self.me['x'], self.me['y']])
        try:
            self.clientSocket.sendto(message, (self.server_ip, self.port))
            data, server = receive(self.timer, self.clientSocket)

            if data[0] == 4:
                self.update_others(data[1:])
            else:
                print('unexpected packet ? {}'.format(data))
            self.timeout_count = 0
        except socket.timeout:
            self.timeout_count += 1
            if self.timeout_count > 10:
                self.stop = True
                print('client give up: 10 timeouts in a row')

    def update_others(self, data):
        n = data[0]
        other_players = data[1:]
        for i in range(n):
            player_data = other_players[i * 3: i * 3 + 3]
            if player_data[0] in self.other_players:
                self.other_players[player_data[0]]['x'] = player_data[1]
                self.other_players[player_data[0]]['y'] = player_data[2]
            else:
                self.other_players[player_data[0]] = {
                    'x': player_data[1],
                    'y': player_data[2],
                }


@time_it
def receive(sock):
    return sock.recvfrom(2048)


interval = 0.05  # 50 milliseconds


if __name__ == '__main__':

    host = sys.argv[1]  # set to server ip or hostname
    port = 25565

    game = Game(host, interval)
    game.start()

    # clientSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # clientSocket.settimeout(timeout)

    # # message = bytearray([1] * message_bytes)

    # timer = Timer()

    # for seq in range(number_of_pings):
    #     try:
    #         message = bytearray('hey-{}'.format(seq), encoding='utf-8')
    #         clientSocket.sendto(message, (host, port))
    #         data, server = receive(timer, clientSocket)
    #         # data, server = clientSocket.recvfrom(2048)

    #     except socket.timeout:
    #         print('udp_seq=%d REQUEST TIMED OUT' % (seq))
    #     except KeyboardInterrupt:
    #         timer.summary()
    #         sys.exit()

    # timer.summary()

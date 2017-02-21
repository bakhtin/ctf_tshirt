#!/usr/bin/python3.6
# GLHF

import asyncio, sqlite3, ipaddress, json, datetime
from enum import Enum
from PIL import Image, ImageDraw, ImageFont
from json import JSONEncoder
from hashlib import md5

conn = sqlite3.connect('tshirt.db')
c = conn.cursor()


class Tshirt(object):
    class Size(Enum):
        S, M, L, XL, XXL, XXXL = 1, 2, 3, 4, 5, 6

    class Color(Enum):
        WHITE, BLACK, BLUE, RED, YELLOW = 1, 2, 3, 4, 5

    class EnumEncoder(JSONEncoder):
        def default(self, o):
            return o.name

    def __init__(self, size, color, text_front, text_back, font_color):
        try:
            self.size = self.Size(size)
        except ValueError:
            raise
        try:
            self.color = self.Color(color)
        except ValueError:
            raise
        self.text_front = str(text_front)
        self.text_back = str(text_back)
        try:
            self.font_color = self.Color(font_color)
        except ValueError:
            raise

    def __str__(self):
        return 'Size: {}, Color: {}, Text on the front: {}, Text on the back: {}, Font color: {}'.format(self.size.name,
                                                                                                         self.color.name,
                                                                                                         self.text_front,
                                                                                                         self.text_back,
                                                                                                         self.font_color)

    def add_text(self, output_file):
        img = Image.open("tshirt_%s.jpeg" % self.color.name.lower())
        draw = ImageDraw.Draw(img)
        font = ImageFont.truetype("sans-serif.ttf", 48)
        draw.text((253, 276), "%s" % self.text_front, self.font_color.name, font=font)
        draw.text((879, 276), "%s" % self.text_back, self.font_color.name, font=font)
        img.save(output_file)

    def save_to_db(self, peer_id):
        order = json.dumps(self.__dict__, cls=Tshirt.EnumEncoder)
        now_datetime = str(datetime.datetime.now())
        c.execute("INSERT INTO `order` VALUES (NULL, ?, ?, ?, ?)", (order,
                                                                    peer_id,
                                                                    now_datetime,
                                                                    md5((order + now_datetime).encode()).hexdigest()))
        conn.commit()
        order_id = c.lastrowid
        c.execute("INSERT INTO `order_status` VALUES (?, (SELECT id FROM `status` WHERE status_text='New'))",
                  (order_id,))
        conn.commit()
        return order_id


@asyncio.coroutine
def main_loop(reader, writer, c=c):
    # Obtain peer_id
    peer_addr = ipaddress.ip_address(writer.get_extra_info('peername')[0]).packed
    peer_addr = int.from_bytes(peer_addr, byteorder='big')
    print("IP: %s connected" % writer.get_extra_info('peername')[0])
    try:
        c.execute("INSERT INTO `user` VALUES (NULL, ?)", (peer_addr,))
        conn.commit()
        peer_id = c.lastrowid
    except sqlite3.IntegrityError:
        c.execute("SELECT id FROM `user` WHERE peer_addr = ?", (peer_addr,))
        peer_id = c.fetchone()[0]
    # Start the dialog
    writer.write(b"Welcome to the Fancy T-Shirts Shop!\r\nMake your own t-shirt print!\r\n")
    while True:
        writer.write(b"Please choose an action:\r\n"
                     b"1) Print constructor\r\n"
                     b"2) My orders\r\n"
                     b"3) Exit\r\n")
        menu_item = yield from reader.read(1024)
        menu_item = menu_item.strip()
        if menu_item == b"3":
            writer.write(b"See you later. Bye\r\n")
            writer.close()
            print("IP: %s disconnected" % writer.get_extra_info('peername')[0])
            break
        # Menu item 1
        elif menu_item == b"1":
            # Color selection
            while True:
                writer.write(b"Choose the color of t-shirt:\r\nAvailable colors: %s\r\n" %
                             (str(['%s: %s' % (c.value, c.name) for c in Tshirt.Color]).strip('[]')).encode())
                color = yield from reader.read(1024)
                try:
                    color = int(color.strip())
                    if color in [c.value for c in Tshirt.Color]:
                        writer.write(b"Color: %s\r\n" % Tshirt.Color(color).name.encode())
                        break
                    else:
                        writer.write(b"Not a valid color. Pick one from available\r\n")
                except ValueError:
                    writer.write(b"Not a valid color. Pick one from available\r\n")
                    continue
            # Size selection
            while True:
                writer.write(b"Choose the size of t-shirt:\r\nAvailable sizes: %s\r\n" %
                             str(['%s: %s' % (s.value, s.name) for s in Tshirt.Size]).strip('[]').encode())
                size = yield from reader.read(1024)
                try:
                    size = int(size.strip())
                    if size in [s.value for s in Tshirt.Size]:
                        writer.write(b"Size: %s\r\n" % Tshirt.Size(size).name.encode())
                        break
                    else:
                        writer.write(b"Not a valid size. Pick one from available\r\n")
                except ValueError:
                    writer.write(b"Not a valid size. Pick one from available\r\n")
            # Text on the front
            writer.write(b"The text that will be printed on the t-shirt's front. You can leave it blank\r\n> ")
            f_text = yield from reader.read(1024)
            f_text = f_text.strip().decode()
            # Text on the back
            writer.write(b"The text that will be printed on the t-shirt's back. You can leave it blank\r\n> ")
            b_text = yield from reader.read(1024)
            b_text = b_text.strip().decode()
            while True:
                writer.write(b"Choose the font color:\r\nAvailable colors: %s\r\n" %
                             str(['%s: %s' % (c.value, c.name) for c in Tshirt.Color]).strip('[]').encode())
                font_color = yield from reader.read(1024)
                try:
                    font_color = int(font_color.strip())
                    if font_color in [c.value for c in Tshirt.Color]:
                        writer.write(b"Font color: %s\r\n" % Tshirt.Color(font_color).name.encode())
                        break
                    else:
                        writer.write(b"Not a valid font color. Pick one from available\r\n")
                except ValueError:
                    writer.write(b"Not a valid font color. Pick one from available\r\n")
            tshirt = Tshirt(size, color, f_text, b_text, font_color)
            writer.write(("T-shirt: Color - {}, Size - {}, Text front - {}, Text back - {}, Font color - {}\r\n".format(
                tshirt.color.name, tshirt.size.name, tshirt.text_front, tshirt.text_back, tshirt.font_color.name
            )).encode())
            yield from writer.drain()
            while True:
                writer.write(b"Would you like to place the order? (y/n)  ")
                yn_response = yield from reader.read(1024)
                yn_response = yn_response.strip()
                if yn_response == b"y":
                    tshirt.add_text("/tmp/t-shirt_1.jpg")
                    order_id = tshirt.save_to_db(peer_id)
                    writer.write(b"You successfully placed the order. Order #%s.\r\n"
                                 b"You will need it to pick up the t-shrit\r\n" % str(order_id).encode())
                    break
                elif yn_response == b"n":
                    break
        # Menu item 2
        elif menu_item == b"2":
            writer.write(b"Your orders\r\n")
            for row in c.execute("SELECT * FROM `order` WHERE user_id = ?", (peer_id,)):
                c.execute(
                    "SELECT status_text FROM status WHERE id=(SELECT status_id FROM order_status WHERE order_id=?)",
                    (row[0],))
                order_status = c.fetchone()[0]
                writer.write(b"-----------\r\n")
                writer.write(b"Order id: %s\r\n\t parameters: %s\r\n\t date: %s\r\n" % (str(row[0]).encode(),
                                                                                         str(row[1]).encode(),
                                                                                         str(row[3]).encode()))
                writer.write(b"Status: %s\r\n" % order_status.encode())
                writer.write(b"-----------\r\n")
            yield from writer.drain()

            writer.write(b"Would you like to pay the order with a coupon?  (y/n)  ")
            yn_response = yield from reader.read(1024)
            yn_response = yn_response.strip()
            if yn_response == b"n":
                writer.write(b"\r\nOkay. You can always pay cash on a pick up\r\n")
                continue
            elif yn_response == b"y":
                writer.write(b"\r\nChoose the order ID to pay for: \r\n")
                order_id = yield from reader.read(1024)
                order_id = order_id.strip()
                try:
                    order_id = int(order_id.decode())
                    c.execute("select order_id from order_status where status_id=1 and order_id=(select id from `order` where user_id = ?)", (peer_id,))
                    peer_order_ids = c.fetchall()
                    peer_order_ids = [o[0] for o in peer_order_ids]
                    if order_id in peer_order_ids:
                        attempts = 3
                        c.execute("SELECT coupon FROM coupon WHERE order_id=?", (order_id,))
                        valid_coupon = c.fetchone()[0]
                        while attempts >= 0:
                            writer.write(b"Please, enter coupon code to pay with: \r\n")
                            peer_coupon = yield from reader.read(1024)
                            peer_coupon = (peer_coupon.strip()).decode()
                            if peer_coupon == valid_coupon:
                                c.execute("UPDATE order_status SET status_id=2 WHERE order_id=?", (order_id,))
                                conn.commit()
                                c.execute(
                                    "SELECT flag_data FROM flag WHERE id=(SELECT flag_id FROM coupon WHERE order_id=?)",
                                    (order_id,))
                                writer.write(
                                    b"You successfully paid the order. Your secret is: %s\r\n" % (c.fetchone()[0]).encode())
                                break
                            else:
                                writer.write(b"Wrong coupon code. Try again. You have %s attempts remaining\r\n" % str(attempts).encode())
                                attempts -= 1
                    else:
                        raise ValueError
                except ValueError:
                    writer.write(b"Not a valid order ID or already paid\r\n")


loop = asyncio.get_event_loop()
coro = asyncio.start_server(main_loop, '0.0.0.0', 8888, loop=loop)
server = loop.run_until_complete(coro)

# Serve requests until Ctrl+C is pressed
print('Serving on {}'.format(server.sockets[0].getsockname()))
try:
    loop.run_forever()
except KeyboardInterrupt:
    pass

# Close the server
server.close()
loop.run_until_complete(server.wait_closed())
loop.close()


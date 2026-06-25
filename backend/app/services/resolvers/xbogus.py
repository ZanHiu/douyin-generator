import base64
import hashlib
import time


class XBogus:
    def __init__(self, user_agent: str | None = None) -> None:
        self._array = [
            None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None,
            None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None,
            None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None,
            0, 1, 2, 3, 4, 5, 6, 7, 8, 9, None, None, None, None, None, None, None, None, None, None, None,
            None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None,
            None, None, None, None, None, None, None, None, None, None, None, None, 10, 11, 12, 13, 14, 15,
        ]
        self._character = "Dkdpgh4ZKsQB80/Mfvw36XI1R25-WUAlEi7NLboqYTOPuzmFjJnryx9HVGcaStCe="
        self._ua_key = b"\x00\x01\x0c"
        self._user_agent = user_agent or (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )

    def _md5_str_to_array(self, md5_str: str) -> list[int]:
        if isinstance(md5_str, str) and len(md5_str) > 32:
            return [ord(char) for char in md5_str]

        result: list[int] = []
        index = 0
        while index < len(md5_str):
            result.append((self._array[ord(md5_str[index])] << 4) | self._array[ord(md5_str[index + 1])])
            index += 2
        return result

    def _md5(self, input_data: str | list[int]) -> str:
        data = self._md5_str_to_array(input_data) if isinstance(input_data, str) else input_data
        md5_hash = hashlib.md5()
        md5_hash.update(bytes(data))
        return md5_hash.hexdigest()

    def _md5_encrypt(self, url_path: str) -> list[int]:
        hashed = self._md5(self._md5_str_to_array(self._md5(url_path)))
        return self._md5_str_to_array(hashed)

    def _encoding_conversion(self, *values: int) -> str:
        payload = [values[0]]
        payload.extend(int(value) for value in values[1:])
        return bytes(payload).decode("ISO-8859-1")

    @staticmethod
    def _encoding_conversion2(first: int, second: int, payload: str) -> str:
        return chr(first) + chr(second) + payload

    @staticmethod
    def _rc4_encrypt(key: bytes, data: bytes) -> bytearray:
        state = list(range(256))
        j = 0
        encrypted = bytearray()

        for index in range(256):
            j = (j + state[index] + key[index % len(key)]) % 256
            state[index], state[j] = state[j], state[index]

        i = j = 0
        for byte in data:
            i = (i + 1) % 256
            j = (j + state[i]) % 256
            state[i], state[j] = state[j], state[i]
            encrypted.append(byte ^ state[(state[i] + state[j]) % 256])

        return encrypted

    def _calculation(self, first: int, second: int, third: int) -> str:
        value = ((first & 255) << 16) | ((second & 255) << 8) | (third & 255)
        return (
            self._character[(value & 16515072) >> 18]
            + self._character[(value & 258048) >> 12]
            + self._character[(value & 4032) >> 6]
            + self._character[value & 63]
        )

    def build(self, url: str) -> tuple[str, str, str]:
        ua_md5_array = self._md5_str_to_array(
            self._md5(
                base64.b64encode(
                    self._rc4_encrypt(self._ua_key, self._user_agent.encode("ISO-8859-1"))
                ).decode("ISO-8859-1")
            )
        )
        empty_md5_array = self._md5_str_to_array(
            self._md5(self._md5_str_to_array("d41d8cd98f00b204e9800998ecf8427e"))
        )
        url_md5_array = self._md5_encrypt(url)

        timer = int(time.time())
        ct = 536919696

        new_array = [
            64,
            0.00390625,
            1,
            12,
            url_md5_array[14],
            url_md5_array[15],
            empty_md5_array[14],
            empty_md5_array[15],
            ua_md5_array[14],
            ua_md5_array[15],
            timer >> 24 & 255,
            timer >> 16 & 255,
            timer >> 8 & 255,
            timer & 255,
            ct >> 24 & 255,
            ct >> 16 & 255,
            ct >> 8 & 255,
            ct & 255,
        ]

        xor_result = new_array[0]
        for value in new_array[1:]:
            if isinstance(value, float):
                value = int(value)
            xor_result ^= value
        new_array.append(xor_result)

        first_half: list[int] = []
        second_half: list[int] = []
        index = 0
        while index < len(new_array):
            first_half.append(new_array[index])
            if index + 1 < len(new_array):
                second_half.append(new_array[index + 1])
            index += 2

        merged = first_half + second_half
        garbled = self._encoding_conversion2(
            2,
            255,
            self._rc4_encrypt(
                "ÿ".encode("ISO-8859-1"),
                self._encoding_conversion(*merged).encode("ISO-8859-1"),
            ).decode("ISO-8859-1"),
        )

        xbogus = ""
        index = 0
        while index < len(garbled):
            xbogus += self._calculation(
                ord(garbled[index]),
                ord(garbled[index + 1]),
                ord(garbled[index + 2]),
            )
            index += 3

        signed_url = f"{url}&X-Bogus={xbogus}"
        return signed_url, xbogus, self._user_agent

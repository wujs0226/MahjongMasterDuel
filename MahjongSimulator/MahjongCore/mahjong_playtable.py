# -*- coding: utf-8 -*-
import random

from mahjong_meld import Meld
from mahjong_tile import Tile


class MahjongBoard:
    round = 0
    dealer_seat = 0
    Walls = None  ## 4 Walls contains the Walls, in our game
    Wannpai = None  ## 王牌,latest 14 cards
    Rinshann = None  ## 岭上,latest 4 cards
    Kan_bonus_indicator = None
    Kan_inside_bonus_indicator = None
    Rivers = None
    Hands = None
    current_player = 0
    expose_indicator_number = 1
    current_step = {0: "draw", 1: "discard", 2: "reaction"}

    def __init__(self):
        self.Walls = []
        for i in range(136):
            self.Walls.append(i)
        random.shuffle(self.Walls)
        self.Wannpai = self.Walls[-14:]
        self.Walls = self.Walls[:-14]
        self.Rinshann = self.Wannpai[:4]
        self.Kan_bonus_indicator = [self.Wannpai[4:][i] for i in range(10) if i % 2 == 0]
        self.Kan_inside_bonus_indicator = [self.Wannpai[4:][i] for i in range(10) if i % 2 == 1]
        # todo: 修正发牌函数
        self.Hands = []
        self.Rivers = []
        for i in range(4):
            self.Rivers.append([])
            self.Hands.append(self.Walls[:13])
            self.Walls = self.Walls[13:]

    def draw(self, player):
        self.Hands[player].append(self.Walls[0])

    def discard(self, player, no):
        if no < 0:
            print("player ", player, "declare win!")
            #todo: finish 胡的流程
        hand = self.Hands[player]
        discard_tile = hand[no]
        hand = hand[:no] + hand[no + 1:]
        self.Hands[player] = hand
        self.Rivers[player].append(discard_tile)

    def print(self):
        print("Hands:")
        for i in range(4):
            print("player ", i, "'s Hands:", Tile.t136_to_g(self.Hands[i]))
        print("bonus_indicator:")
        print(Tile.t136_to_g(self.Kan_bonus_indicator))
        print(Tile.t136_to_g(self.Kan_inside_bonus_indicator))
        print("Remain Walls:")
        print(len(self.Walls), "tiles remain:", Tile.t136_to_g(self.Walls))


class GameTable:
    # players
    bot = None
    opponents = None
    # game round info
    dealer_seat = 0
    bonus_indicator = None
    round_number = 0
    reach_sticks = 0
    honba_sticks = 0
    count_players = 4
    count_remaining_tiles = 0
    revealed_tiles = None
    # rule
    open_tanyao = False
    aka_dora = False

    def __init__(self, ai_obj, opponent_class, thcleint):
        self._init_players(ai_obj, opponent_class, thcleint)
        self.bonus_indicator = []
        self.revealed_tiles = [0] * 34

    def __str__(self):
        bonus_tile_indicator_repr = Tile.t136_to_g(self.bonus_indicator)
        return 'Round number:{0}, Honba sticks:{1}, Bonus tile indicator:{2}'.format(
            self.round_number, self.honba_sticks, bonus_tile_indicator_repr
        )

    def _init_players(self, ai_obj, opponent_class, thclient):
        self.bot = ai_obj
        self.bot.thclient = thclient
        self.bot.dealer_seat = self.dealer_seat
        self.bot.game_table = self
        self.opponents = []
        for seat in range(1, self.count_players):
            opponent = opponent_class(seat, self.dealer_seat)
            opponent.game_table = self
            self.opponents.append(opponent)

    def init_round(self, round_number, honba_sticks, reach_sticks, bonus_tile_indicator, dealer_seat, scores):
        self.round_number = round_number
        self.honba_sticks = honba_sticks
        self.reach_sticks = reach_sticks
        self.revealed_tiles = [0] * 34
        self.bonus_indicator = []
        for indicator in bonus_tile_indicator:
            self.add_bonus_indicator(indicator)
        self.dealer_seat = dealer_seat

        self.bot.init_state()
        self.bot.dealer_seat = dealer_seat
        for opponent in self.opponents:
            opponent.init_state()
            opponent.dealer_seat = dealer_seat
        self.set_players_scores(scores)

        self.count_remaining_tiles = 136 - 14 - self.count_players * 13  # 14 - 十四张王牌，不能被任何玩家摸到

        if round_number == 0 and honba_sticks == 0:
            seats = [0, 1, 2, 3]
            for i in range(0, self.count_players):
                self.get_player(i).initial_seat = seats[i - dealer_seat]

    def call_meld(self, by_whom, meld):  # not called by own, i.e. by_whom != 0
        self.count_remaining_tiles += 1
        if meld.type == Meld.KAN or meld.type == Meld.CHANKAN:
            self.count_remaining_tiles -= 1
        self.get_player(by_whom).call_meld(meld)
        tiles = meld.tiles[:]
        if meld.called_tile in tiles:
            tiles.remove(meld.called_tile)
        if meld.type == Meld.CHANKAN:
            tiles = [meld.tiles[0]]
        for tile in tiles:
            self._add_revealed_tile(tile)

    def call_reach(self, by_whom):
        self.get_player(by_whom).call_reach()
        self.reach_sticks += 1

    def discard_tile(self, by_whom, tile):
        self.count_remaining_tiles -= 1
        self.get_player(by_whom).discard_tile(tile)
        self._add_revealed_tile(tile)
        for opp in self.opponents:
            if opp.reach_status:
                opp.add_safe_tile(tile // 4)

    def _add_revealed_tile(self, tile):
        self.revealed_tiles[tile // 4] += 1

    def set_players_scores(self, scores, uma=None):
        # set scores for players
        for i in range(0, self.count_players):
            self.get_player(i).score = scores[i] * 100
            if uma:
                self.get_player(i).uma = uma[i]
        # set tmp rank position for players
        scores_for_rank = [[i, scores[i]] for i in range(4)]
        scores_for_rank = sorted(scores_for_rank, key=lambda x: x[1])
        for i in range(4):
            self.get_player(scores_for_rank[i][0]).tmp_rank = i

    def set_personal_info(self, names_and_levels):
        for i in range(0, 4):
            self.get_player(i).name = names_and_levels[i]['name']
            self.get_player(i).level = names_and_levels[i]['level']

    def add_bonus_indicator(self, tile):
        self.bonus_indicator.append(tile)
        self._add_revealed_tile(tile)

    def get_player(self, index):
        if index == 0:
            return self.bot
        else:
            return self.opponents[index - 1]

    def get_opponents(self):
        res = []
        for i in range(1, 4):
            res.append(self.get_player(i))
        return res

    @property
    def round_wind(self):
        return Tile.WINDS[self.round_number // 4]

    @property
    def bonus_tiles(self):
        bonus_dict = {8: 0, 17: 9, 26: 18, 30: 27, 33: 31}
        return [bonus_dict.get(t // 4, t // 4 + 1) for t in self.bonus_indicator]

    @property
    def last_round_discard(self):
        return [self.get_player(i).discard34[-1] for i in range(1, 4) if len(self.get_player(i).discard34) > 0]

    @property
    def dangerous(self):
        return self.has_reach or (self.has_high_fan and self.bot.turn_num > 6)

    @property
    def last_two_round_discard(self):
        return [t for i in range(0, 4) for t in self.get_player(i).discard34[-2:]]

    def last_three_round_discard(self, opp_index):
        discards = []
        for i in range(1, 4):
            opp_opp_index = (opp_index + i) % 4
            discards.append(self.get_player(opp_opp_index).discard34)
        res = []
        for j in range(1, 3):
            for d in discards:
                if len(d) >= j:
                    res.append(d[-j])
        return res

    @property
    def recent_discard(self):
        num = max(0, 5 - len(self.bot.discard34) // 3)
        res = []
        for i in range(0, 4):
            if len(self.get_player(i).discard34) > 0:
                res += self.get_player(i).discard34[-num:]
        return res

    @property
    def barrier_safe_tiles(self):
        res = []
        for tile in range(0, 27):
            if tile % 9 == 0 or tile % 9 == 8:
                continue
            if self.revealed_tiles[tile] == 4:
                tile % 9 == 1 and res.append(tile - 1)
                tile % 9 == 2 and (res.append(tile - 1) or res.append(tile - 2))
                tile % 9 == 3 and (res.append(tile - 1) or res.append(tile - 2))
                tile % 9 == 4 and (res.append(tile - 2) or res.append(tile + 2))
                tile % 9 == 5 and (res.append(tile + 1) or res.append(tile + 2))
                tile % 9 == 6 and (res.append(tile + 1) or res.append(tile + 2))
                tile % 9 == 7 and res.append(tile + 1)
        return res

    @property
    def has_kan(self):
        return len(self.bonus_tiles) - 1 > 0

    @property
    def kan_num(self):
        return len(self.bonus_tiles) - 1

    @property
    def num_reaches(self):
        return len([i for i in range(1, 4) if self.get_player(i).reach_status])

    @property
    def has_reach(self):
        for i in range(1, 4):
            if self.get_player(i).reach_status:
                return True
        return False

    @property
    def has_high_fan(self):
        for i in range(1, 4):
            if self.get_player(i).cnt_open_bonus_tiles > 2:
                return True
        return False

    @property
    def revealed_feature(self):
        return [min(t / 4, 1) for t in self.revealed_tiles]

    @property
    def scores(self):
        return [self.get_player(i).score for i in range(0, 4)]

    @property
    def opp_scores(self):
        return [self.get_player(i).score for i in range(1, 4)]

    @property
    def last_discard(self):
        if len(self.get_player(3).discard34) > 0:
            return self.get_player(3).discard34[-1]
        return -1


if __name__ == '__main__':
    board = MahjongBoard()
    board.print()

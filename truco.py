from pygame.locals import *
from pygame.sprite import *
from pygame import Surface
import pygame
import os, sys
import random
import gym
import numpy as np

def clear_terminal():
    os.system("cls" if os.name == "nt" else "clear")

# Global
DECKLIST = ["01a", "01b", "01c", "01d", "02a", "02b", "02c", "02d",
        "03a", "03b", "03c", "03d", "04a", "04c", "04d",
        "05a", "05b", "05c", "05d", "06a", "06b", "06c", "06d",
        "07", "08", "09", "10"]
DECKDICT = {}
DATAPATH = "data"
SOUNDPATH = "sounds"
SEED = 9955124

HORIZONTAL = True
VERTICAL = False
NOONE=-1
TEAM1=0
TEAM2=1

DRAW = 1
NOTDRAW = 0

CARDWIDTH = 80
CARDHEIGHT = 124

GAMEWIDTH = 800
GAMEHEIGHT = 600

# Hand positions for each player
P1POS = ( int( GAMEWIDTH/2 - 1.5*CARDWIDTH ), # hand x
        GAMEHEIGHT-CARDHEIGHT,                # hand y
        int((GAMEWIDTH/2) - 0.5*CARDWIDTH),   # played card x
        GAMEHEIGHT-2*CARDHEIGHT )             # played card y

P2POS = ( 0,
        int( GAMEHEIGHT/2 + 0.5*CARDHEIGHT ),
        0 + 2*CARDWIDTH,
        int(GAMEHEIGHT/2 - 0.5*CARDHEIGHT) )

P3POS = ( int((GAMEWIDTH/2) - 1.5*CARDWIDTH),
        0,
        int((GAMEWIDTH/2) - 0.5*CARDWIDTH),
        0 + CARDHEIGHT )

P4POS = ( GAMEWIDTH - CARDWIDTH,
        int( GAMEHEIGHT/2 + 0.5*CARDHEIGHT ),
        GAMEWIDTH - 3*CARDWIDTH,
        int(GAMEHEIGHT/2 - 0.5*CARDHEIGHT) )


# function from https://www.pygame.org/docs/tut/ChimpLineByLine.html
def load_image(name, colorkey=None):
    fullname = os.path.join(DATAPATH, name)
    try:
        image = pygame.image.load(fullname)
    except message:
        print('Cannot load image:', name)
        raise SystemExit
    image = image.convert()
    return image, image.get_rect()

def load_sound(name):
    fullname = os.path.join(SOUNDPATH, name)
    try:
        sound = pygame.mixer.Sound(fullname)
    except Exception:
        print('Cannot load sound')
        raise Exception
    return sound

class Card(pygame.sprite.Sprite):
    def __init__(self, img_name):
        pygame.sprite.Sprite.__init__(self)

        self.original_image, self.rect = load_image(img_name, -1)
        self.image = self.original_image
        self.screen = pygame.display.get_surface()
        self.area = self.screen.get_rect()

    def getImage(self):
        return self.original_image

    def update(self, x, y):
        self.rect.topleft = (x, y)

    def draw(self, x, y):
        self.update(x, y)
        self.image = self.original_image

    def drawBack(self, x, y, back):
        self.update(x, y)
        self.image = back


class Hand(object):
    def __init__(self, screen, show, pos, horizontal, back):
        self.screen = screen
        self.show = show
        self.back = back
        self.base_x, self.base_y = pos[0], pos[1]
        self.played_x, self.played_y = pos[2], pos[3]
        self.horizontal = horizontal

        self.cards = []
        self.playedcards = []
        self.rendercards = RenderClear()
        self.renderplayed = GroupSingle()

    def setHand(self, cardlist):
        self.clear()
        self.cards = cardlist
        for card in cardlist:
            self.rendercards.add(DECKDICT[card])

    def getHand(self):
        return(self.cards)

    def clear(self):
        self.cards = []
        self.playedcards = []
        self.rendercards.empty()
        self.renderplayed.empty()

    def clearPlayed(self):
        self.playedcards = []
        self.renderplayed.empty()

    def draw(self):
        x, y = self.base_x, self.base_y
        for card in self.cards:
            if self.show:
                DECKDICT[card].draw(x, y)
            else:
                DECKDICT[card].drawBack(x, y, self.back.getImage())

            self.rendercards.add(DECKDICT[card])
            if self.horizontal:
                x += CARDWIDTH
            else:
                y -= CARDHEIGHT
        self.rendercards.draw(self.screen)

        x, y = self.played_x, self.played_y
        for card in self.playedcards:
            DECKDICT[card].draw(x, y)
            self.renderplayed.add(DECKDICT[card])
        self.renderplayed.draw(self.screen)


    def play(self, card):
        try:
            self.cards.remove(card)
        except Exception:
            print("Error removing card:\nCard doesn't exist\n")
            raise Exception

        self.setHand(self.getHand())
        self.playedcards = [card]
        self.rendercards.remove(DECKDICT[card])
        self.renderplayed.add(DECKDICT[card])

        return 1

    def Show(show):
        self.show = show

class TrucoEnv(object):

    def __init__(self, players, screen, background, fanSound, playSound):
        self.players = players
        self.screen = screen
        self.background = background
        self.fanSound = fanSound
        self.playSound = playSound

        # TODO:
        self.cards = [0, 0, 0, 0] # Change card order
        self.round_points = [0,0]
        self.first = None
        self.turn = None
        self.round_num = None
        self.round_value = None
        self.truco = None
        self.lastPlayWasTruco = None
        self.first_team_win = None

        # DEBUG
        self.debug = ""

        self.player = None
        self.total_points = [0,0]

        # Environment
        self.actionSpace = ["1", "2", "3", "T", "Q"]

        self.action_space = gym.spaces.Discrete(5)
        self.observation_space = gym.spaces.Discrete(12)
        self.num_envs = 1

    def isTerminalState(self):
        if max(self.total_points[0], self.total_points[1]) >= 12:
            return True
        else:
            return False

    def getState(self):
        state = []

        playerhand = list()
        playerhand.extend(self.players[self.player].getHand())
        while(len(playerhand) < 3):
            playerhand.append("00a")

        for i in range(0, 3):
            playerhand[i] = int(playerhand[i][0:2])

        round_points = list(self.round_points)
        if self.team(self.player) == 1:
            round_points[0] = self.round_points[1]
            round_points[1] = self.round_points[0]

        total_points = list(self.total_points)
        if self.team(self.player) == 1:
            total_points[0] = self.total_points[1]
            total_points[1] = self.total_points[0]

        if self.first_team_win == -1:
            first_team_win = -1
        elif self.first_team_win == self.team(self.player):
            first_team_win = 1
        else:
            first_team_win = 0

        state.extend(playerhand)
        state.extend(self.cards)
        state.extend(round_points)
        state.extend(total_points)
        state.extend([self.turn, self.round_num, self.round_value, self.truco, self.lastPlayWasTruco, first_team_win])


        return np.array(state, dtype=np.int32)

    def step(self, action):
        reward = [0,0]
        if not self.illegalMove(action):
            reward, round_end = self.play(action)
            resultingState = self.getState()
            return resultingState, reward, self.isTerminalState(), round_end

        else:
            reward = [-1,-1]
            round_end = False
            terminalState = False
            actualState = self.getState()
            return actualState, reward, terminalState, round_end

    def illegalMove(self, action):
        if action == "Q" or action == 5:
            if self.lastPlayWasTruco:
                return False
            else:
                return True

        elif action == "T" or action == 4:
            team = self.team(self.player)
            if not self.lastPlayWasTruco and (self.truco == team):
                return True
            elif self.round_value >= 12:
                return True
            else:
                return False

        elif not self.lastPlayWasTruco:
            if action == "3" or action == 3:
                if self.round_num >= 1:
                    return True
                else:
                    return False

            elif action == "2" or action == 2:
                if self.round_num >= 2:
                    return True
                else:
                    return False
            elif action == "1" or action == 1 or action == "Q" or action == 5:
                return False

            else:
                return True
        else:
            return True

    def reset(self, next=False):
        if(not next):
            self.total_points = [0, 0]
            self.first = 0
        else:
            self.first = (self.first+1) %2

        self.round_points = [0, 0]
        self.shuffleHands()

        #self.draw()
        self.player = 0
        self.turn = 0
        self.round_num = 0
        self.round_value = 1
        self.truco = NOONE
        self.lastPlayWasTruco = False
        self.first_team_win = -1

        return self.getState()

    def shuffleHands(self):
        random.shuffle(DECKLIST)
        self.players[0].setHand((DECKLIST[0:3]))
        self.players[1].setHand((DECKLIST[3:6]))
        self.players[2].setHand((DECKLIST[6:9]))
        self.players[3].setHand((DECKLIST[9:12]))

        if(len(self.players[3].getHand()) < 3 ):
            print("Not enough cards!")
            raise Exception

        self.cards = [0, 0, 0, 0]

    def nextPlayer(self):
        return (self.player+1) % 4

    def lastPlayer(self):
        if self.player == 0:
            return 3
        else:
            return self.player-1

    def team(self, player):
        return self.player%2

    def play(self, action):
        reward = [0, 0]
        round_end = False

        if action == "Q" or action == 5:
            winner = self.nextPlayer()
            team = (self.player+1)%2
            reward, round_end = self.point(team)


        elif action == "1" or action == "2" or action == "3" or action == 1 or action == 2 or action == 3:
            card = int(action)

            self.debug = self.player
            try:
                card = self.players[self.player].getHand()[card-1]
            except:
                self.printInfo()
                print(self.cards)
                print(card)
                print(action)
                print(self.players[0].getHand())
                print(self.players[1].getHand())
                print(self.players[2].getHand())
                print(self.players[3].getHand())
                raise Exception
            self.players[self.player].play(card)
            self.cards[self.turn] = int(card[0:2]) # card value


            if self.turn >= 3:
            # Resolve round
                highest_card = 0
                winround = False
                winplayer = -1
                player = 0
                for card in self.cards:
                    if(card > highest_card):
                        highest_card = card
                        winround = True
                        winplayer = player
                    elif(card == highest_card):
                        winround = False
                    player += 1

                if winround:
                    team = self.team(winplayer)
                    if self.round_num == 0:
                        self.first_team_win = team
                    self.round_points[team] += 1
                else:
                    self.round_points[0] += 2
                    self.round_points[1] += 2

                # Check if draw or a team won
                t0, t1 = self.round_points[0], self.round_points[1]
                if t0 == 6 and t1 == 6: # game draw
                    reward, round_end = self.point(-1)
                elif (abs(t0-t1) >= 1) and (max(t0,t1) >= 2): # player won
                    if t0 > t1:
                        reward, round_end = self.point(0)
                    elif t0 < t1:
                        reward, round_end = self.point(1)
                    else:
                        print("Impossible State")
                        raise Exception
                elif t0 == 3 and t1 == 3: # each team won a round and the last was draw
                    reward, round_end = self.point(self.first_team_win)

                else: # If no one won or didnt draw, go to next round
                    self.nextRound(first=winplayer) # Player who won is going to play first

            else:
                self.player = self.nextPlayer()
                self.turn = self.turn+1

        elif action == "T" or action == 4:
            if not self.lastPlayWasTruco:
                self.lastPlayWasTruco = True
                self.truco = self.team(self.player)
                self.player = self.nextPlayer()
                self.turn = self.turn+1
            else:
                self.lastPlayWasTruco = False
                self.player = self.lastPlayer()
                self.turn = self.turn -1
                if self.round_value == 1:
                    self.round_value -=1
                self.round_value += 3

        return reward, round_end

    def point(self, team):
        reward = [0, 0]

        if team != -1:
            self.total_points[team] += self.round_value
            if team == 0:
                reward = [self.round_value, -self.round_value]
            else:
                reward = [-self.round_value, self.round_value]

        # Start new round
        self.shuffleHands()
        self.round_points = [0,0]
        self.first = (self.first+1)%4

        self.nextRound()
        self.round_num = 0
        self.round_value = 1
        self.truco = NOONE
        self.lastPlayWasTruco = 0
        self.first_team_win = -1

        round_end = True

        return reward, round_end

    def nextRound(self, first=None):
        # Erase played cards from last round
        if first == None:
            first = self.first

        self.cards = [0,0,0,0]
        self.player = first
        self.turn = 0
        self.round_num += 1

        reward = 0
        return reward

    def printInfo(self):
        print("Total points\n{} vs {}".format(self.total_points[0], self.total_points[1]))
        print("Round points\n{} vs {}".format(self.round_points[0], self.round_points[1]))
        print("\nRound {}, Value = {}".format(self.round_num, self.round_value))
        print("Turn {}".format(self.turn))
        print("Player {}".format(self.player))
        print("\nDebug: {}".format(self.debug))

    def render(self):
        self.screen.blit(self.background, (0, 0))
        for player in self.players:
            player.draw()
        pygame.display.flip()
        clear_terminal()
        self.printInfo()

def setupGame(show_all = False, SEED = 42):
    # load cards
    pygame.init()
    screen = pygame.display.set_mode((GAMEWIDTH, GAMEHEIGHT))
    pygame.display.set_caption("Truco")
    pygame.display.update()

    for img_name in os.listdir(DATAPATH):
        if img_name == "back01.gif":
            BACK1 = Card(img_name)
        elif img_name == "back02.gif":
            BACK2 = Card(img_name)
        elif img_name == "back03.gif":
            BACK3 = Card(img_name)
        elif img_name == "back04.gif":
            BACK4 = Card(img_name)
        elif img_name == "back05.gif":
            BACK5 = Card(img_name)
        elif img_name[0:4] != "back":
            DECKDICT[img_name[0:-4]] = Card(img_name)
        else:
            print("Image not identified!")
            raise Exception

    # load sounds
    pygame.mixer.init(22100, -8, 1, 4)
    fanSound = load_sound("cardFan.wav")
    playSound = load_sound("cardPlay.wav")


    # background
    background = Surface(screen.get_size())
    background = background.convert()
    background.fill((0, 128, 0))

    screen.blit(background, (0, 0))

    # players
    random.seed(SEED)
    players = [None, None, None, None]
    players[0] = Hand(screen, True, P1POS, HORIZONTAL, BACK1)
    players[1] = Hand(screen, show_all, P2POS, VERTICAL, BACK5)
    players[2] = Hand(screen, show_all, P3POS, HORIZONTAL, BACK3)
    players[3] = Hand(screen, show_all, P4POS, VERTICAL, BACK4)

    game = TrucoEnv(players, screen, background, fanSound, playSound)
    return game


if __name__ == "__main__":
    setupGame()

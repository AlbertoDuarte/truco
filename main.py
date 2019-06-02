from pygame.locals import *
from pygame.sprite import *
from pygame import Surface
import pygame
import os, sys
import random

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
SEED = 41

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

        self.image, self.rect = load_image(img_name, -1)
        screen = pygame.display.get_surface()
        self.area = screen.get_rect()

    def update(self, x, y):
        self.rect.topleft = (x, y)

class Hand():
    def __init__(self, screen, show, pos, horizontal):
        self.screen = screen
        self.show = show
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
            DECKDICT[card].update(x, y)
            self.rendercards.add(DECKDICT[card])
            if self.horizontal:
                x += CARDWIDTH
            else:
                y -= CARDHEIGHT
        self.rendercards.draw(self.screen)

        x, y = self.played_x, self.played_y
        for card in self.playedcards:
            DECKDICT[card].update(x, y)
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

class Game():
    def __init__(self, players, screen, background, fanSound, playSound):
        self.players = players
        self.screen = screen
        self.background = background
        self.fanSound = fanSound
        self.playSound = playSound


    def draw(self):
        self.screen.blit(self.background, (0, 0))
        for player in self.players:
            player.draw()
        pygame.display.flip()

    def wait(self):
        print("Press a key to continue")
        KEY_PRESSED = False
        while not KEY_PRESSED:
            for event in pygame.event.get():
                if event.type == QUIT:
                    exit()
                elif event.type == KEYDOWN:
                    KEY_PRESSED = True
        clear_terminal()

    def clearBoard(self):
        for player in self.players:
            player.clearPlayed()
        pygame.display.flip()

    def playCard(self, player, team, acceptTruco = False):
        HAS_PLAYED = False
        PLAY = False
        while not HAS_PLAYED:
            for event in pygame.event.get():
                if event.type == QUIT:
                    exit()
                elif event.type == KEYDOWN:
                    key = pygame.key.name(event.key)
                    hand = player.getHand()
                    if key == "a":
                        if(len(hand) >= 1 and not acceptTruco):
                            card = hand[0]
                            PLAY = True

                    elif key == "s":
                        if(len(hand) >= 2 and not acceptTruco):
                            card = hand[1]
                            PLAY = True

                    elif key == "d":
                        if(len(hand) >= 3 and not acceptTruco):
                            card = hand[2]
                            PLAY = True

                    elif key == "t":
                        if(self.truco == NOONE or self.truco != team or acceptTruco):
                            card = "truco"
                            HAS_PLAYED = True

                    elif key == "y":
                        card = "out"
                        HAS_PLAYED = True

                    if PLAY:
                        pygame.mixer.Sound.play(self.playSound)
                        player.play(card)
                        HAS_PLAYED = True
                        break

            pygame.time.Clock().tick(15)
        return card

    def acceptTruco(self, player, team):
        play = self.playCard(player, team, acceptTruco = True)
        if play == "truco":
            if self.round_value == 1:
                self.round_value = 3
            else:
                self.round_value += 3
                return("truco")
        else:
            return("out")

    def playRound(self, first):
        cards = [None, None, None, None]
        bigger_card = [0, 0] # bigger card each team has played
        turn = first % 4
        winner = -1
        i = 0
        while(i <= 3):
            team = turn%2
            card = self.playCard(self.players[turn], team)
            if card == "out":
                winner = (team+1) % 2 # the other team wins
                break

            elif card == "truco":
                clear_terminal()
                print("Player {} asked for Truco!".format(turn+1))
                play = self.acceptTruco(self.players[(turn+1)%4], (team+1)%2)
                if play == "out":
                    winner = team
                    break
                self.truco = team
                acc = (turn+1)%4
                print("Player {} accepted Player {}'s Truco".format( acc+1, turn+1 ))

            else:
                card = int(card[0:2])
                if turn % 2 == 0:
                    bigger_card[0] = max(bigger_card[0], card)
                else:
                    bigger_card[1] = max(bigger_card[1], card)
                i+=1
                turn = (turn+1) % 4

            self.draw()

        if winner == -1: # if no one gave up yet
            if bigger_card[0] > bigger_card[1]:
                    return([1,0], NOTDRAW)
            elif bigger_card[0] < bigger_card[1]:
                    return([0,1], NOTDRAW)
            else:
                return([2,2], DRAW)

        else:
            if winner == TEAM1:
                return([3,0], NOTDRAW)
            elif winner == TEAM2:
                return([0,3], NOTDRAW)
            else:
                print("Winner != -1 but no one won\n")
                raise

    def playGame(self):
        total_points = [0, 0]
        first = 0

        while(total_points[0] < 12 and total_points[1] < 12):
            print("aaa")
            random.shuffle(DECKLIST)
            self.players[0].setHand((DECKLIST[0:3]))
            self.players[1].setHand((DECKLIST[3:6]))
            self.players[2].setHand((DECKLIST[6:9]))
            self.players[3].setHand((DECKLIST[9:12]))
            self.draw()
            self.round_value = 1
            self.truco = NOONE
            round_points = [0, 0]
            clear_terminal()
            print("TEAM 1: {}".format(total_points[0]))
            print("TEAM 2: {}".format(total_points[1]))

            round_num = 0
            end = False
            self.fanSound.play()
            while not end:
                round_num += 1
                points, status = self.playRound(first)
                round_points[0] += points[0]
                round_points[1] += points[1]

                if(round_points[0] == 6 and round_points[1] == 6):
                    end = True
                    clear_terminal()
                    print("Empate!!!")


                elif(abs(round_points[0]-round_points[1]) >= 1 and max(round_points[0],round_points[1]) >= 2):
                    end = True
                    clear_terminal()
                    if(round_points[0] > round_points[1]):
                        total_points[0] += self.round_value
                        print("Team 1 won {} points".format(self.round_value))
                    elif(round_points[0] < round_points[1]):
                        total_points[1] += self.round_value
                        print("Team 2 won {} points".format(self.round_value))

                self.wait()
                self.clearBoard()
                self.draw()

            first = (first+1)%4

        if(total_points[0] > total_points[1]):
            print("Team 1 wins!")
        else:
            print("Team 2 wins!")


def main():
    # load cards
    pygame.init()
    screen = pygame.display.set_mode((GAMEWIDTH, GAMEHEIGHT))
    pygame.display.update()

    for img_name in os.listdir(DATAPATH):
        if img_name != "back.gif":
            DECKDICT[img_name[0:-4]] = Card(img_name)

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
    players[0] = Hand(screen, True, P1POS, HORIZONTAL)
    players[1] = Hand(screen, True, P2POS, VERTICAL)
    players[2] = Hand(screen, True, P3POS, HORIZONTAL)
    players[3] = Hand(screen, True, P4POS, VERTICAL)

    clear_terminal()
    game = Game(players, screen, background, fanSound, playSound)
    game.playGame()


if __name__ == "__main__":
    main()

import gym
import truco

from pygame.locals import *
from pygame.sprite import *
from pygame import Surface
import pygame
from train import PPO, Memory
import torch

import random


def wait():
    print("Press a key to continue")
    KEY_PRESSED = False
    while not KEY_PRESSED:
        for event in pygame.event.get():
            if event.type == QUIT:
                exit()
            elif event.type == KEYDOWN:
                KEY_PRESSED = True

def playCard():
    HAS_PLAYED = False
    while not HAS_PLAYED:
        for event in pygame.event.get():
            if event.type == QUIT:
                exit()
            elif event.type == KEYDOWN:
                key = pygame.key.name(event.key)
                if key == "a":
                    return 1

                elif key == "s":
                    return 2

                elif key == "d":
                    return 3

                elif key == "t":
                    return 4

                elif key == "q":
                    return 5

name = input("file name: ")
############## Hyperparameters ##############
# creating environment
seed = random.randint(1, 1000000000)
env = truco.setupGame(show_all=True, SEED=seed)
state_dim = 17
action_dim = 5
render = True
max_timesteps = 500
n_latent_var = 64           # number of variables in hidden layer
lr = 0.00002
betas = (0.9, 0.999)
gamma = 0.99                # discount factor
K_epochs = 4                # update policy for K epochs
eps_clip = 0.2              # clip parameter for PPO
#############################################

memory = Memory()
ppo = PPO(state_dim, action_dim, n_latent_var, lr, betas, gamma, K_epochs, eps_clip)
ppo.policy_old.load_state_dict(torch.load(name), map_location="cpu") # Change
episode_done = False

state = env.reset()
while not episode_done:
    env.render()
    if env.player == 0:
        action = playCard()
    else:
        action = ppo.policy_old.act(state, memory)
        action += 1
        wait()
    if not env.illegalMove(action):
        state, reward, episode_done, done = env.step(action)
        env.render()

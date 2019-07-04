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

#name = input("file name: ")
############## Hyperparameters ##############
env_name = "compare"
# creating environment
seed = random.randint(1, 1000000000)
env = truco.setupGame(show_all=True, SEED=seed)
state_dim = 17
action_dim = 5
render = False
max_timesteps = 500
max_episodes = 1000
n_latent_var = 64           # number of variables in hidden layer
lr = 0.00002
betas = (0.9, 0.999)
gamma = 0.99                # discount factor
K_epochs = 4                # update policy for K epochs
eps_clip = 0.2              # clip parameter for PPO
#############################################

memory4 = Memory()
agent4 = PPO(state_dim, action_dim, n_latent_var, lr, betas, gamma, K_epochs, eps_clip)
agent4.policy_old.load_state_dict(torch.load("PPO-v3-4agents/PPO_Truco-v3_EP500000.pth", map_location="cpu")) # Change

memory1 = Memory()
agent1 = PPO(state_dim, action_dim, n_latent_var, lr, betas, gamma, K_epochs, eps_clip)
agent1.policy_old.load_state_dict(torch.load("PPO-v3-1agent/PPO_Truco-vE0_EP500000.pth", map_location="cpu")) # Change

episode_done = False

win_t0, win_t1 = 0, 0
i_episode = 0;
ep = 0
state = env.reset()
for i_episode in range(max_episodes):
    state = env.reset()
    for t in range(max_timesteps):
        done = False
        while not done:
            if env.player == 0 or env.player == 2:
                action = agent4.policy_old.act(state, memory4)
                action += 1
            else:
                action = agent1.policy_old.act(state, memory1)
                action += 1
            if not env.illegalMove(action):
                state, reward, episode_done, done = env.step(action)
                if render:
                    env.render()
                    
        memory4.clear_memory()
        memory1.clear_memory()
                    
        if episode_done:
            ep += 1
            if env.total_points[0] > env.total_points[1]:
                win_t0 += 1
            else:
                win_t1 += 1
                    
            break
                
print("\nApos {} partidas, 4agents ganhou {} e 1agent ganhou {}!".format( max_episodes, win_t0, win_t1))
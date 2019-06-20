import torch
import torch.nn as nn
from torch.distributions import Categorical
import gym
import numpy as np

import truco

device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")

class Memory:
    def __init__(self):
        self.actions = []
        self.states = []
        self.logprobs = []
        self.rewards = []

    def clear_memory(self):
        del self.actions[:]
        del self.states[:]
        del self.logprobs[:]
        del self.rewards[:]

class ActorCritic(nn.Module):
    def __init__(self, state_dim, action_dim, n_latent_var):
        super(ActorCritic, self).__init__()
        self.affine = nn.Linear(state_dim, n_latent_var)

        # actor
        self.action_layer = nn.Sequential(
                nn.Linear(state_dim, n_latent_var),
                nn.Tanh(),
                nn.Linear(n_latent_var, n_latent_var),
                nn.Tanh(),
                nn.Linear(n_latent_var, action_dim),
                nn.Softmax(dim=-1)
                )

        # critic
        self.value_layer = nn.Sequential(
                nn.Linear(state_dim, n_latent_var),
                nn.Tanh(),
                nn.Linear(n_latent_var, n_latent_var),
                nn.Tanh(),
                nn.Linear(n_latent_var, 1)
                )

    def forward(self):
        raise NotImplementedError

    def act(self, state, memory):
        state = torch.from_numpy(state).float().to(device)
        action_probs = self.action_layer(state)
        dist = Categorical(action_probs)
        action = dist.sample()

        memory.states.append(state)
        memory.actions.append(action)
        memory.logprobs.append(dist.log_prob(action))

        return action.item()

    def evaluate(self, state, action):
        action_probs = self.action_layer(state)
        dist = Categorical(action_probs)

        action_logprobs = dist.log_prob(action)
        dist_entropy = dist.entropy()

        state_value = self.value_layer(state)

        return action_logprobs, torch.squeeze(state_value), dist_entropy

class PPO:
    def __init__(self, state_dim, action_dim, n_latent_var, lr, betas, gamma, K_epochs, eps_clip):
        self.lr = lr
        self.betas = betas
        self.gamma = gamma
        self.eps_clip = eps_clip
        self.K_epochs = K_epochs

        self.policy = ActorCritic(state_dim, action_dim, n_latent_var).to(device)
        self.optimizer = torch.optim.Adam(self.policy.parameters(),
                                              lr=lr, betas=betas)
        self.policy_old = ActorCritic(state_dim, action_dim, n_latent_var).to(device)

        self.MseLoss = nn.MSELoss()

    def update(self, memory):
        # Monte Carlo estimate of state rewards:
        rewards = []
        discounted_reward = 0
        for reward in reversed(memory.rewards):
            discounted_reward = reward + (self.gamma * discounted_reward)
            rewards.insert(0, discounted_reward)

        # Normalizing the rewards:
        rewards = torch.tensor(rewards).to(device)
        rewards = (rewards - rewards.mean()) / (rewards.std() + 1e-5)

        # convert list to tensor
        old_states = torch.stack(memory.states).to(device).detach()
        old_actions = torch.stack(memory.actions).to(device).detach()
        old_logprobs = torch.stack(memory.logprobs).to(device).detach()

        # Optimize policy for K epochs:
        for _ in range(self.K_epochs):
            # Evaluating old actions and values :
            logprobs, state_values, dist_entropy = self.policy.evaluate(old_states, old_actions)

            ############################
            #MODIFICATION: MULTIPLY ENTROPY
            dist_entropy *= 2
            ################################

            # Finding the ratio (pi_theta / pi_theta__old):
            ratios = torch.exp(logprobs - old_logprobs.detach())

            # Finding Surrogate Loss:
            advantages = rewards - state_values.detach()
            surr1 = ratios * advantages
            surr2 = torch.clamp(ratios, 1-self.eps_clip, 1+self.eps_clip) * advantages
            loss = -torch.min(surr1, surr2) + 0.5*self.MseLoss(state_values, rewards) - 0.01*dist_entropy

            # take gradient step
            self.optimizer.zero_grad()
            loss.mean().backward()
            self.optimizer.step()

        # Copy new weights into old policy:
        self.policy_old.load_state_dict(self.policy.state_dict())

def main():
    ############## Hyperparameters ##############
    env_name = "Truco-v1"
    # creating environment
    env = truco.setupGame()
    state_dim = 17
    action_dim = 5
    render = False
    log_interval = 20           # print avg reward in the interval
    max_episodes = 2500         # max training episodes
    max_timesteps = 300         # max timesteps in one episode
    n_latent_var = 64           # number of variables in hidden layer
    #update_timestep = 50        # update policy every n timesteps
    update = 1                  # update every n episodes
    lr = 0.00002
    betas = (0.9, 0.999)
    gamma = 0.99                # discount factor
    K_epochs = 4                # update policy for K epochs
    eps_clip = 0.2              # clip parameter for PPO
    random_seed = None
    #############################################

    #if random_seed:
    #    torch.manual_seed(random_seed)
    #    env.seed(random_seed)

    memory = list()
    models = list()
    for i in range(0, 4):
        models.append(PPO(state_dim, action_dim, n_latent_var, lr, betas, gamma, K_epochs, eps_clip))
        memory.append(Memory())
    print(lr,betas)
    print(len(memory))

    # logging variables
    running_reward_p0 = 0
    avg_length = 0
    timestep = 0

    # training loop
    for i_episode in range(1, max_episodes+1):
        state = env.reset()
        for t in range(max_timesteps):
            timestep += 1

            played = [False, False, False, False]
            running_reward = [[], [], [], []]
            done = False
            # Running policy_old:
            while not done:
                player = env.player
                team = env.team(player)
                action = models[player].policy_old.act(state, memory[player])
                action += 1
                state, reward, episode_done, done = env.step(action)
                if len(state) != 17:
                    print("Error!")
                    raise ValueError
                # Saving reward:
                played[player] = True

                team = env.team(player)
                running_reward[player].append(reward[team])

            for i in range(0, 4):
                if len(running_reward[i]) > 0:
                    team = env.team(i)
                    running_reward[i][-1] = reward[team]
                    memory[i].rewards.extend(running_reward[i])


            for i in running_reward[0]:
                running_reward_p0 += i

            if render:
                env.render()
            if episode_done:
                if env.total_points[0] > env.total_points[1]:
                    final_reward = [12, -12, 12, -12]
                else:
                    final_reward = [-12, 12, -12, 12]

                for i in range(0, 4):
                    memory[i].rewards[-1] = final_reward[i]
                break

        # Update models
        if i_episode % update == 0:
            for i in range(0, 4):
                models[i].update(memory[i])
                memory[i].clear_memory()
        avg_length += t

        # logging
        if i_episode % log_interval == 0:
            avg_length = int(avg_length/log_interval)
            running_reward_p0 = int((running_reward_p0/log_interval))

            print('Episode {} \t avg length: {} \t reward p0: {}'.format(i_episode, avg_length, running_reward_p0))
            running_reward_p0 = 0
            avg_length = 0

    torch.save(models[0].policy.state_dict(), './PPO_{}.pth'.format(env_name))


if __name__ == '__main__':
    main()

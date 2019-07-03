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
    env_name = "Truco-vE0"
    # creating environment
    env = truco.setupGame()
    state_dim = 17
    action_dim = 5
    render = False
    log_interval = 25000       # print avg reward in the interval
    max_episodes = 1000000         # max training episodes
    max_timesteps = 300         # max timesteps in one episode
    n_latent_var = 64           # number of variables in hidden layer
    #update_timestep = 50       # update policy every n timesteps
    update = 1                  # update every n episodes
    lr = 0.00002
    betas = (0.9, 0.999)
    gamma = 0.99                # discount factor
    K_epochs = 4                # update policy for K epochs
    eps_clip = 0.2              # clip parameter for PPO
    
    win_first_turn = 0
    not_win_first_turn = 0
    
    legal_move_counter = 0
    illegal_move_counter = 0
    
    giveup_counter = 0
    truco_called_counter = 0
    
    truco_called_pe = 0
    not_truco_called_pe = 0

    
    best_card = 0
    middle_card = 0
    worst_card = 0
    
    random_seed = None
    save_model = 50000
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
            first_team_win = -1
            # Running policy_old:
            while not done:
                player = env.player
                team = env.team(player)
                action = models[player].policy_old.act(state, memory[player])
                action += 1
                ############################################
                # Game History
                if env.player == 0:
                    if env.illegalMove(action):
                        illegal_move_counter += 1
                    
                    else:
                        legal_move_counter += 1
                        if not env.illegalMove(5):  #counting times a legal give up action was possible(enemy called truco)
                            truco_called_counter += 1
                        if (action == 5 or action == '5') and not env.illegalMove(action):  # counting times a legal give up action was taken
                            giveup_counter += 1

                        if (action == 4 or action == '4') and env.turn == 3 and not env.lastPlayWasTruco: # Truco called (not counting accepted truco) as 'foot'
                            truco_called_pe += 1
                        else:
                            not_truco_called_pe += 1

                        if env.turn == 0 and int(action) <= 3 and env.round_num == 0:
                            first_card_played = env.players[env.player].getHand()[int(action)-1]
                            cards = env.players[env.player].getHand()
                            cards.sort()
                            equals = [(x == first_card_played) for x in cards]
                            
                            # On first turn and first round, calculate what card was played
                            if equals[0] and equals[1] and equals[2]:
                                equal_card += 1
                                
                            elif equals[2]:
                                best_card += 1
                                
                            elif equals[0]:
                                worst_card += 1
                            
                            elif equals[1]:
                                middle_card += 1

                ###########################################
                
                state, reward, episode_done, done = env.step(action)
                if len(state) != 17:
                    print("Error!")
                    raise ValueError
                # Saving reward:
                played[player] = True

                team = env.team(player)
                running_reward[player].append(reward[team])
                
                first_team_win = env.first_team_win
            

            for i in range(0, 1):
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
                    
                    if first_team_win == 0:
                        # Counting if won first round and first turn
                        win_first_turn += 1
                    else:
                        not_win_first_turn += 1
                        
                else:
                    final_reward = [-12, 12, -12, 12]

                for i in range(0, 1):
                    memory[i].rewards[-1] = final_reward[i]
                break
            
        # Players 1 and 3 receives old model from player 0
        models[1].policy_old.load_state_dict(models[0].policy_old.state_dict())
        models[3].policy_old.load_state_dict(models[0].policy_old.state_dict())

        # Update models
        if i_episode % update == 0:
            for i in range(0, 1):
                models[i].update(memory[i])
                memory[i].clear_memory()
        avg_length += t
        
        # Player 2 receives player 0 model AFTER the update
        models[2].policy_old.load_state_dict(models[0].policy_old.state_dict())

        if i_episode % save_model == 0:
            torch.save(models[0].policy.state_dict(), './PPO_{}_EP{}.pth'.format(env_name, i_episode))

        # logging
        if i_episode % log_interval == 0:
            avg_length = int(avg_length/log_interval)
            running_reward_p0 = int((running_reward_p0/log_interval))

            print('Episode {} \t avg length: {} \t reward p0: {} \t give up percent: {}'.format(i_episode, avg_length, running_reward_p0, (giveup_counter/truco_called_counter)*100))
            print("First turn, first round: best {}  middle {}  worst {}".format(best_card, middle_card, worst_card))
            print("legal moves {}  illegal moves  {}".format(legal_move_counter, illegal_move_counter))
            print("truco pe    {}  not truco pe   {}".format(truco_called_pe, not_truco_called_pe))
            print("win 1 turn  {}  not win 1 turn {}".format(win_first_turn, not_win_first_turn))
            print("truco acc   {}  truco give up  {}".format(truco_called_counter, giveup_counter))
            print("\n")
            
            
            giveup_counter = 0
            truco_called_pe = 0
            truco_called_counter = 0
            running_reward_p0 = 0
            avg_length = 0
            best_card = worst_card = middle_card = 0

    torch.save(models[0].policy.state_dict(), './PPO_{}.pth'.format(env_name))


if __name__ == '__main__':
    main()

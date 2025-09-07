import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import gym

# 超参数的设定
BATCH_SIZE = 128
LR = 0.01
GAMMA = 0.9
EPSILON = 0.9
MEMORY_CAPACITY = 2000
Q_NETWORK_ITERATION = 100

# 获取互动的环境
env = gym.make("CartPole-v0", render_mode="human").unwrapped
NUM_ACTIONS = env.action_space.n
NUM_STATES = env.observation_space.shape[0]
print(NUM_ACTIONS, NUM_STATES)
ENV_A_SHAPE = 0 if isinstance(env.action_space.sample(), int) else env.action_space.sample.shape


class Net(nn.Module):
    def __init__(self):
        super(Net, self).__init__()
        self.fc1 = nn.Linear(NUM_STATES, 50)  # input layer
        self.fc1.weight.data.normal_(0, 0.1)
        self.fc2 = nn.Linear(50, 30)
        self.fc2.weight.data.normal_(0, 0.1)
        self.out = nn.Linear(30, NUM_ACTIONS)  # output layer
        self.out.weight.data.normal_(0, 0.1)

    def forward(self, x):
        x = self.fc1(x)
        x = F.relu(x)
        x = self.fc2(x)
        x = F.relu(x)
        action_prob = self.out(x)
        return action_prob


class DQN():
    def __init__(self):
        super(DQN, self).__init__()
        # 分别用于计算 Q(S,A) 和 Q(S',a)
        # 去使用 TargetQ 网络
        self.eval_net, self.target_net = Net(), Net()

        self.learn_step_counter = 0
        self.memory_counter = 0
        # *2 是因为 transition 中包括当前时刻的状态和下一时刻的状态，每一时刻的状态是一维数组array
        # +2 是因为要存放 action 和 reward
        self.memory = np.zeros((MEMORY_CAPACITY, NUM_STATES * 2 + 2))

        self.optimizer = torch.optim.Adam(self.eval_net.parameters(), lr=LR)
        self.loss_func = nn.MSELoss()

    def choose_action(self, state):
        state = torch.unsqueeze(torch.FloatTensor(state), 0)  # 把state转成pytorch的tensor张量，并且得到一维数组形式
        # ε greedy
        if np.random.randn() <= EPSILON:
            # Greedy policy
            action_value = self.eval_net.forward(state)  # 得到Q预测, 同时拿到多个 action 对应的Q 值
            action = torch.max(action_value, 1)[1].data.numpy()  # 取出具体的一个值
            action = action[0] if ENV_A_SHAPE == 0 else action.reshape(ENV_A_SHAPE)
        else:
            # random policy
            action = np.random.randint(0, NUM_ACTIONS)
            action = action if ENV_A_SHAPE == 0 else action.reshape(ENV_A_SHAPE)
        return action

    def store_transition(self, state, action, reward, next_state):
        transition = np.hstack((state, [action, reward], next_state))
        index = self.memory_counter % MEMORY_CAPACITY
        self.memory[index, :] = transition
        self.memory_counter += 1

    def learn(self):
        # 更新参数

        # 每隔一定的迭代次数，将target net更新一下
        if self.learn_step_counter % Q_NETWORK_ITERATION == 0:
            self.target_net.load_state_dict(self.eval_net.state_dict())

        self.learn_step_counter += 1

        # 从memory里面采样获取一个批次的数据
        sample_index = np.random.choice(MEMORY_CAPACITY, BATCH_SIZE)
        batch_memory = self.memory[sample_index, :]

        batch_state = torch.FloatTensor(batch_memory[:, :NUM_STATES])
        batch_action = torch.LongTensor(batch_memory[:, NUM_STATES:NUM_STATES + 1].astype(int))
        batch_reward = torch.FloatTensor(batch_memory[:, NUM_STATES + 1:NUM_STATES + 2])
        batch_next_state = torch.FloatTensor(batch_memory[:, -NUM_STATES:])

        # 根据Qlearning的公式来计算TD error以及loss
        # q_eval 计算的是 Q(S,A) 或者叫 y_pred
        q_eval = self.eval_net(batch_state).gather(1, batch_action)  # 选择其中一个
        # q_next 计算的是 Q(S',a)
        q_next = self.target_net(batch_next_state).detach()
        # 得到 y_true
        q_target = batch_reward + GAMMA * q_next.max(1)[0].view(BATCH_SIZE, 1)
        loss = self.loss_func(q_eval, q_target)

        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()


def reward_func(env, x, x_dot, theta, theta_dot):
    # env.x_threshold 这个变量代表小推车在轨道上可以移动的最大距离阈值。如果推车超过这个范围，任务就会失败
    # abs(x) 求绝对值，x代表着小推车当前的横向位置。
    # env.x_threshold - abs(x) 这一部分代表了小推车当前位置与阈值之间的相对距离, 并且我们海可以将起归一化到 -0.5 到 0.5 之间
    r1 = (env.x_threshold - abs(x)) / env.x_threshold - 0.5
    # env.theta_threshold_radians 杆子倾斜的最大角度阈值（以弧度为单位）。这个阈值定义了杆子倾斜的最大容忍度
    # abs(theta) 杆子当前的倾斜角度的绝对值，用来衡量杆子偏离垂直状态的程度
    # env.theta_threshold_radians - abs(theta) 类似于 x 的计算，这部分计算了杆子倾斜角度和阈值之间的相对差距，并且进行了归一化
    # 杆子完全垂直时奖励等于 0.5，杆子倾斜值阈值时奖励等于 -0.5
    r2 = (env.theta_threshold_radians - abs(theta)) / env.theta_threshold_radians - 0.5
    reward = r1 + r2
    return reward


def main():
    dqn = DQN()
    episodes = 400
    print("Collecting Experience...")
    for i in range(episodes):
        state, _ = env.reset()  # 初始化重置环境，得到一开始的状态
        ep_reward = 0
        while True:
            env.render()
            action = dqn.choose_action(state)
            # 可以根据 env 给出的 reward 进行调整，也可以选择直接不去使用人家给的 reward
            next_state, _, done, _, info = env.step(action)
            # 而是自己根据 state 状态来去设计一个 reward 计算方式
            x, x_dot, theta, theta_dot = next_state
            reward = reward_func(env, x, x_dot, theta, theta_dot)

            dqn.store_transition(state, action, reward, next_state)
            ep_reward += reward

            if dqn.memory_counter >= MEMORY_CAPACITY:
                dqn.learn()
                if done:
                    print("episode: {}, the episode reward is {}".format(i, round(ep_reward, 3)))

            if done:
                break

            state = next_state


if __name__ == '__main__':
    main()

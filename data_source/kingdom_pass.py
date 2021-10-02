from pprint import pformat


class KingdomPass:
    def __init__(self, data):
        self.start = data['StartDate']
        self.end = data['EndDate']
        self.rewards = [KingdomPassReward(stage) for stage in data['RewardStageArray']]

    def __str__(self):
        return pformat(self.rewards, indent=2)


class KingdomPassReward:
    def __init__(self, data):
        self.rewards = [self.transform_reward(r) for r in data['RewardArray']]
        self.pass_rewards = [self.transform_reward(r) for r in data['PassRewardArray']]

    @staticmethod
    def transform_reward(stage):
        amount = stage['Amount']
        reward_type = translate_reward_type(stage)
        return reward_type, amount

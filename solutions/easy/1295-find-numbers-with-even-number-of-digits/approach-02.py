# LeetCode: Find Numbers with Even Number of Digits
# Problem ID: 1295
# Difficulty: Easy
# Language: python
# Approach: 02
# Submission ID: 2083505861
class Solution(object):
    def findNumbers(self, nums):
        a=0
        for i in range(len(nums)):
            digits=len(str( nums[i]))
            if digits%2==0:
                a+=1
        return a

        
# LeetCode: Find Numbers with Even Number of Digits
# Problem ID: 1295
# Difficulty: Easy
# Language: python
# Approach: 01
# Submission ID: 2083521377
class Solution(object):
    def findNumbers(self, nums):
        a=0
        for i in nums:
            temp=i
            digits=0
            
            while temp>0:
                temp//=10
                digits+=1
            if digits%2==0:
                a+=1
        return a

        
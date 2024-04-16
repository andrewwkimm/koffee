Feature: koffee APIs

    Scenario Outline: User gets a translated video file
        Given a user has a basic <language> video file

    Examples: language
        | language |
        | English  |
        | Korean   |

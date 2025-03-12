# To Do List

## Gmail integration

[X] Utilize the prompt to continue iterating on gmail integration
[X] Determine what communications we want in app and what we don't
[X] Make sure both outgoing and incoming email from contacts in the app are tracked

## Text integration

[] Not sure what we need here, but we'll work on it

## Pipeline

[X] Visual representation on the Dashboard page
[] A Pipeline page for people
[] A Pipeline page for churches

## Administation

### Offices

[] Create the ability to have various offices see only their people and churches
[]
[]

### Users

[] Determine what data everyone should see and what data only the individual user should see
[] Implement the above (certain data seen by all in an office and certain data seen only by the individual user)
[] Determine permissions and how to structure that

## Expanding the app to other Organizations

[] Determine if we want to create structures for other orgs to make changes
[] If so, implement some type of API structure allowing orgs to put in their logos, colors, etc...
[] Other. . .

## Debugging

[X] Make sure users only see their tasks and their communications
[X] Fix people not showing up on Dashboard page
[X] Fix Communications page 500 Internal Server Error
[X] Change Email signatures to not show the raw text and only show the HTML below the message body
[X] Clicking on a person returns the user to the dashboard instead of opening the person detail page.
[X] Clicking Edit from within a church or person a 'Method not allowed' message
[X] Communications still showing up in John Doe's loginin...  he should not have any communications. I thin Jim's communications are showing up for him... Need to fix this.
[] Get rid of any 'Connection' buttons anywhere in the app... all connections should happen at initial login making these buttons redundant.
[X] Email signatures should be specific to users and not accross users in the app
[] Person detail pg not showing the pipeline at the top of page
[] Tried to register a sent text message in the communications and got an error: 'An error occurred: local variable 'recipient_name' referenced before assignment'
[] Similar to above when trying to register In-Person meeting: 'An error occurred: local variable 'recipient_name' referenced before assignment'... same with video call, other, and phone call
[] Clicked on Add Task from a person detail page and it diverted to the task page
[] On task page error: 'An unexpected error occurred. Please try again later.'
[] When trying to create a church when I click 'Create Church' button it reverts to the churches page and I get the message: 'An error occurred while creating the church. Please try again.'
[] Church dynamic search not working

## New or Upgraded Functions

[X] Wrap everything under the divider on sidebar into one page called Settings
[] Church detail page needs to show all fields... should look more like the person detail page w/ Church pipeline across the top and Add Task button and Recent communications on bottom
[] When creating a user from Super Admin or Office Admin
[] Need ability to edit users in Administration
[] Need a place/way to see what the various permission are and what each allows and/or disallows
[] Under administration the System Settings button doesn't do anything

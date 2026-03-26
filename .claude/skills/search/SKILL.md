# SE Knowledge Search

Search across all SE knowledge sources to find answers, content, and tribal knowledge.

## Triggers

Use this skill when the user asks:
- "Has anyone worked on X?"
- "Does anyone have a slide/deck/doc about X?"
- "Any documentation around X?"
- "How do we handle X?"
- "What's our positioning on X?"
- "Find me content about X"
- "Search for X"

## Instructions

When searching for SE knowledge, query multiple sources in parallel and synthesize the results.

### Step 1: Understand the Query

Determine what type of information the user needs:
- **Discussion/Q&A**: Search Slack first
- **Sales content/slides**: Search Highspot and Google Drive
- **Customer conversations**: Search Gong
- **Technical docs**: Search Google Drive and Slack

### Step 2: Search All Relevant Sources

Call these tools in parallel based on relevance:

**For general questions ("Has anyone worked on X?"):**
```
slack.search_messages(query="X")
gong.search_calls(query="X")
```

**For content requests ("Any slides about X?"):**
```
highspot.search(query="X")
google_workspace.search_drive(query="X")
```

**For process/how-to questions:**
```
slack.search_messages(query="X how")
google_workspace.search_drive(query="X")
```

### Step 3: Synthesize Results

Present findings organized by:

1. **Most relevant results first** - prioritize exact matches
2. **Source attribution** - always include where you found it
3. **Who to contact** - message author, call participant, doc owner
4. **Recency** - note when the information was created/shared
5. **Direct links** - include URLs to the source material

### Response Format

```markdown
## Summary
[1-2 sentence answer to the question]

## Found in Slack
- [Quote or summary] - @person in #channel (date)
  [Link to message]

## Found in Gong
- [Summary of relevant call moment] - Call with [company] (date)
  Participants: [names]
  [Link or call ID]

## Found in Highspot
- [Content title] - [type: deck, doc, video]
  [Description]
  [Link]

## Found in Google Drive
- [Document title]
  [Relevant excerpt]
  [Link]

## Suggested Next Steps
- Reach out to @person who has experience with this
- Review [specific doc/deck] for the latest positioning
```

### Tips

- Use Slack search modifiers: `in:#channel`, `from:@user`, `has:link`
- For Gong, search for product names, competitor names, or objection keywords
- Check both recent and older content - tribal knowledge accumulates
- If no results found, suggest who might know or where to ask

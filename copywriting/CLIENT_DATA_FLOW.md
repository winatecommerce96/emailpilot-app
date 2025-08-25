# Client Data Flow in Copywriting Module

## Overview
The copywriting module pulls client data from Firestore at multiple points to ensure brand consistency throughout the copy generation and refinement process.

## Data Flow Points

### 1. Initial Copy Generation (`/api/generate-copy`)
✅ **PULLS CLIENT DATA**

When generating the initial 5 variants:
- Fetches client document from Firestore: `db.collection("clients").document(client_id)`
- Extracts comprehensive brand context:
  ```python
  brand_context = {
      "name": client_data.get("name"),
      "industry": client_data.get("industry"),
      "voice": client_data.get("brand_voice"),
      "tone": client_data.get("brand_tone"),
      "personality": client_data.get("brand_personality"),
      "values": client_data.get("brand_values"),
      "target_audience": client_data.get("target_audience"),
      "emoji_usage": client_data.get("emoji_usage"),
      "formality_level": client_data.get("formality_level"),
      "key_messages": client_data.get("key_messages"),
      "unique_selling_points": client_data.get("unique_selling_points"),
      "competitor_differentiation": client_data.get("competitor_differentiation")
  }
  ```
- This context is passed to EVERY variant generation
- Used in AI prompts to maintain brand consistency

### 2. Copy Refinement (`/api/refine`)
✅ **NOW PULLS CLIENT DATA** (Just Fixed!)

When refining a variant:
- Re-fetches fresh client data from Firestore for each refinement
- Includes additional fields for refinement:
  - `prohibited_words`: Words to avoid in copy
  - `preferred_phrases`: Phrases to incorporate
  - All brand guidelines from initial generation
- Ensures refinements respect brand voice even with creative instructions

### 3. AI Review (`/api/review`)
⚠️ **PARTIALLY USES CLIENT DATA**

When reviewing copy:
- Receives `client_id` in request
- Could fetch brand context but currently doesn't fully utilize it
- Reviews against general best practices

### 4. Client List (`/api/clients`)
✅ **PULLS ALL CLIENTS**

For dropdown population:
- Fetches all clients from Firestore
- Returns ID, name, and industry for selection

## Firestore Schema Used

```javascript
clients/{client_id}: {
  // Basic Info
  name: "Client Name",
  company_name: "Company Name",
  industry: "E-commerce",
  
  // Brand Guidelines
  brand_voice: "professional, friendly",
  brand_tone: "conversational",
  brand_personality: "helpful, innovative",
  brand_values: ["quality", "innovation", "service"],
  
  // Target & Messaging
  target_audience: "25-45 professionals",
  key_messages: ["trusted by thousands", "industry leader"],
  unique_selling_points: ["24/7 support", "free shipping"],
  competitor_differentiation: "faster delivery",
  
  // Content Rules
  emoji_usage: "moderate",  // none, moderate, liberal
  formality_level: "moderate",  // casual, moderate, formal
  prohibited_words: ["cheap", "discount"],
  preferred_phrases: ["premium quality", "exclusive offer"],
  
  // Metadata
  created_at: timestamp,
  updated_at: timestamp
}
```

## How Client Data Affects Output

### Initial Generation
- **Brand Voice/Tone**: Shapes overall writing style
- **Target Audience**: Adjusts language complexity and references
- **Emoji Usage**: Controls emoji inclusion based on creativity level
- **Formality Level**: Caps creativity for formal brands
- **USPs**: Incorporated into value propositions
- **Key Messages**: Woven into body copy

### Refinements
- **All Above PLUS**:
- **Prohibited Words**: Actively avoided in refinements
- **Preferred Phrases**: AI attempts to incorporate these
- **Fresh Data**: Re-fetched to catch any updates

## Testing Client Data Integration

1. **Create Test Client in Firestore**:
```javascript
{
  name: "Test Fashion Brand",
  industry: "Fashion",
  brand_voice: "trendy, youthful",
  brand_tone: "excited, energetic",
  emoji_usage: "liberal",
  formality_level: "casual",
  prohibited_words: ["cheap", "bargain"],
  preferred_phrases: ["runway ready", "fashion forward"]
}
```

2. **Generate Copy**: Should reflect trendy voice with emojis

3. **Refine with Instruction**: "Make it more formal"
   - Should become more formal BUT still avoid prohibited words
   - Should maintain brand values while adjusting tone

## Recommendations for Enhancement

1. **Cache Strategy**: Consider caching client data for session to reduce Firestore reads

2. **Brand Compliance Score**: Add scoring to show how well copy matches brand guidelines

3. **Review Enhancement**: Update `/api/review` to score against specific brand guidelines

4. **Variant Comparison**: Show which variant best matches brand voice

5. **History Tracking**: Store which brand version was used for each generation

## Summary

✅ The copywriting module NOW properly pulls and uses client data from Firestore for:
- Initial copy generation (all 5 variants)
- Copy refinements (with fresh data fetch)
- Client selection dropdown

This ensures brand consistency across all generated and refined copy!
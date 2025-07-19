package steam

import (
	"strings"
)

// ESRBRating represents ESRB rating categories
type ESRBRating string

// ESRB Rating constants
const (
	ESRBRatingEveryone     ESRBRating = "Everyone"
	ESRBRatingEveryone10   ESRBRating = "Everyone 10+"
	ESRBRatingTeen         ESRBRating = "Teen"
	ESRBRatingMature17     ESRBRating = "Mature 17+"
	ESRBRatingAdultsOnly   ESRBRating = "Adults Only 18+"
	ESRBRatingRatingPending ESRBRating = "Rating Pending"
	ESRBRatingUnrated      ESRBRating = "Unrated"
)

// ContentDescriptor represents content warning types
type ContentDescriptor string

// Content descriptor constants based on Steam's content descriptor IDs
const (
	ContentDescriptorViolence           ContentDescriptor = "Violence"
	ContentDescriptorBlood              ContentDescriptor = "Blood"
	ContentDescriptorIntenseViolence    ContentDescriptor = "Intense Violence"
	ContentDescriptorPartialNudity      ContentDescriptor = "Partial Nudity"
	ContentDescriptorNudity             ContentDescriptor = "Nudity"
	ContentDescriptorSexualContent      ContentDescriptor = "Sexual Content"
	ContentDescriptorStrongLanguage     ContentDescriptor = "Strong Language"
	ContentDescriptorMatureHumor        ContentDescriptor = "Mature Humor"
	ContentDescriptorDrugReference      ContentDescriptor = "Drug Reference"
	ContentDescriptorAlcoholReference   ContentDescriptor = "Alcohol Reference"
	ContentDescriptorTobaccoReference   ContentDescriptor = "Tobacco Reference"
	ContentDescriptorGambling           ContentDescriptor = "Gambling"
	ContentDescriptorOnlineInteractions ContentDescriptor = "Online Interactions Not Rated"
)

// ESRBRatingMapper handles mapping Steam content descriptors to ESRB ratings
type ESRBRatingMapper struct {
	// Content descriptor ID to description mapping
	descriptorMap map[int]ContentDescriptor
	
	// Rating rules based on content descriptors
	ratingRules map[ESRBRating][]ContentDescriptor
}

// NewESRBRatingMapper creates a new ESRB rating mapper with predefined rules
func NewESRBRatingMapper() *ESRBRatingMapper {
	mapper := &ESRBRatingMapper{
		descriptorMap: make(map[int]ContentDescriptor),
		ratingRules:   make(map[ESRBRating][]ContentDescriptor),
	}
	
	mapper.initializeDescriptorMap()
	mapper.initializeRatingRules()
	
	return mapper
}

// initializeDescriptorMap sets up the mapping from Steam content descriptor IDs to descriptions
func (m *ESRBRatingMapper) initializeDescriptorMap() {
	m.descriptorMap = map[int]ContentDescriptor{
		1:  ContentDescriptorViolence,
		2:  ContentDescriptorBlood,
		3:  ContentDescriptorIntenseViolence,
		4:  ContentDescriptorPartialNudity,
		5:  ContentDescriptorNudity,
		6:  ContentDescriptorSexualContent,
		7:  ContentDescriptorStrongLanguage,
		8:  ContentDescriptorMatureHumor,
		9:  ContentDescriptorDrugReference,
		10: ContentDescriptorAlcoholReference,
		11: ContentDescriptorTobaccoReference,
		12: ContentDescriptorGambling,
		13: ContentDescriptorOnlineInteractions,
	}
}

// initializeRatingRules sets up rules for determining ESRB ratings based on content descriptors
func (m *ESRBRatingMapper) initializeRatingRules() {
	// Adults Only 18+ - Most restrictive content
	m.ratingRules[ESRBRatingAdultsOnly] = []ContentDescriptor{
		ContentDescriptorNudity,
		ContentDescriptorSexualContent,
	}
	
	// Mature 17+ - Strong content but not adults only
	m.ratingRules[ESRBRatingMature17] = []ContentDescriptor{
		ContentDescriptorIntenseViolence,
		ContentDescriptorBlood,
		ContentDescriptorStrongLanguage,
		ContentDescriptorPartialNudity,
		ContentDescriptorMatureHumor,
		ContentDescriptorGambling,
	}
	
	// Teen - Moderate content
	m.ratingRules[ESRBRatingTeen] = []ContentDescriptor{
		ContentDescriptorViolence,
		ContentDescriptorDrugReference,
		ContentDescriptorAlcoholReference,
		ContentDescriptorTobaccoReference,
	}
	
	// Everyone 10+ - Mild content
	m.ratingRules[ESRBRatingEveryone10] = []ContentDescriptor{
		// Typically determined by mild cartoon violence or minimal suggestive themes
		// These are harder to detect from Steam descriptors alone
	}
	
	// Everyone - No concerning content descriptors
	m.ratingRules[ESRBRatingEveryone] = []ContentDescriptor{
		// Games with no concerning content descriptors
	}
}

// MapContentDescriptors converts Steam content descriptor IDs to human-readable descriptions
func (m *ESRBRatingMapper) MapContentDescriptors(ids []int) []string {
	descriptors := make([]string, 0, len(ids))
	
	for _, id := range ids {
		if desc, exists := m.descriptorMap[id]; exists {
			descriptors = append(descriptors, string(desc))
		}
	}
	
	return descriptors
}

// DetermineESRBRating analyzes content descriptors and notes to determine the most appropriate ESRB rating
func (m *ESRBRatingMapper) DetermineESRBRating(descriptorIDs []int, notes string) ESRBRating {
	// Convert IDs to descriptors
	descriptors := make([]ContentDescriptor, 0, len(descriptorIDs))
	for _, id := range descriptorIDs {
		if desc, exists := m.descriptorMap[id]; exists {
			descriptors = append(descriptors, desc)
		}
	}
	
	// Also analyze notes text for additional context
	notesLower := strings.ToLower(notes)
	
	// Check for Adults Only content (highest priority)
	for _, desc := range m.ratingRules[ESRBRatingAdultsOnly] {
		if m.containsDescriptor(descriptors, desc) || m.containsInNotes(notesLower, desc) {
			return ESRBRatingAdultsOnly
		}
	}
	
	// Check for Mature 17+ content
	matureCount := 0
	for _, desc := range m.ratingRules[ESRBRatingMature17] {
		if m.containsDescriptor(descriptors, desc) || m.containsInNotes(notesLower, desc) {
			matureCount++
		}
	}
	if matureCount > 0 {
		return ESRBRatingMature17
	}
	
	// Check for Teen content
	teenCount := 0
	for _, desc := range m.ratingRules[ESRBRatingTeen] {
		if m.containsDescriptor(descriptors, desc) || m.containsInNotes(notesLower, desc) {
			teenCount++
		}
	}
	if teenCount > 0 {
		return ESRBRatingTeen
	}
	
	// Check notes for Everyone 10+ indicators
	if m.containsInNotes(notesLower, "mild violence") || 
	   m.containsInNotes(notesLower, "cartoon violence") ||
	   m.containsInNotes(notesLower, "fantasy violence") {
		return ESRBRatingEveryone10
	}
	
	// Default to Everyone if no concerning content is found
	if len(descriptors) == 0 && notes == "" {
		return ESRBRatingEveryone
	}
	
	// If we have content descriptors but they don't match known patterns, mark as unrated
	return ESRBRatingUnrated
}

// containsDescriptor checks if a specific content descriptor exists in the list
func (m *ESRBRatingMapper) containsDescriptor(descriptors []ContentDescriptor, target ContentDescriptor) bool {
	for _, desc := range descriptors {
		if desc == target {
			return true
		}
	}
	return false
}

// containsInNotes checks if notes text contains keywords related to a content descriptor
func (m *ESRBRatingMapper) containsInNotes(notesLower string, descriptor ContentDescriptor) bool {
	switch descriptor {
	case ContentDescriptorViolence:
		return strings.Contains(notesLower, "violence") || 
			   strings.Contains(notesLower, "violent")
	case ContentDescriptorBlood:
		return strings.Contains(notesLower, "blood") || 
			   strings.Contains(notesLower, "gore")
	case ContentDescriptorIntenseViolence:
		return strings.Contains(notesLower, "intense violence") || 
			   strings.Contains(notesLower, "graphic violence")
	case ContentDescriptorNudity:
		return strings.Contains(notesLower, "nudity") || 
			   strings.Contains(notesLower, "nude")
	case ContentDescriptorPartialNudity:
		return strings.Contains(notesLower, "partial nudity")
	case ContentDescriptorSexualContent:
		return strings.Contains(notesLower, "sexual") || 
			   strings.Contains(notesLower, "adult content")
	case ContentDescriptorStrongLanguage:
		return strings.Contains(notesLower, "strong language") || 
			   strings.Contains(notesLower, "profanity")
	case ContentDescriptorMatureHumor:
		return strings.Contains(notesLower, "mature humor") || 
			   strings.Contains(notesLower, "crude humor")
	case ContentDescriptorDrugReference:
		return strings.Contains(notesLower, "drug") || 
			   strings.Contains(notesLower, "substance")
	case ContentDescriptorAlcoholReference:
		return strings.Contains(notesLower, "alcohol") || 
			   strings.Contains(notesLower, "drinking")
	case ContentDescriptorGambling:
		return strings.Contains(notesLower, "gambling") || 
			   strings.Contains(notesLower, "betting")
	}
	return false
}

// GetRatingDescription returns a human-readable description of the ESRB rating
func (r ESRBRating) GetDescription() string {
	switch r {
	case ESRBRatingEveryone:
		return "Content is generally suitable for all ages. May contain minimal cartoon, fantasy or mild violence and/or infrequent use of mild language."
	case ESRBRatingEveryone10:
		return "Content is generally suitable for ages 10 and up. May contain more cartoon, fantasy or mild violence, mild language and/or minimal suggestive themes."
	case ESRBRatingTeen:
		return "Content is generally suitable for ages 13 and up. May contain violence, suggestive themes, crude humor, minimal blood, simulated gambling and/or infrequent use of strong language."
	case ESRBRatingMature17:
		return "Content is generally suitable for ages 17 and up. May contain intense violence, blood and gore, sexual themes and/or strong language."
	case ESRBRatingAdultsOnly:
		return "Content suitable only for adults ages 18 and up. May include prolonged graphic and intense violence featuring content unsuitable for adults."
	case ESRBRatingRatingPending:
		return "Rating pending - submitted to the ESRB and awaiting final rating."
	case ESRBRatingUnrated:
		return "Not rated by the ESRB."
	default:
		return "Unknown rating."
	}
}
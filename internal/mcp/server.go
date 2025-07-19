package mcp

import (
	"bufio"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"strconv"

	"github.com/sirupsen/logrus"

	"github.com/jimsantora/steam-librarian/internal/services"
	"github.com/jimsantora/steam-librarian/internal/storage"
	"github.com/jimsantora/steam-librarian/internal/steam"
)

// Server implements the MCP (Model Context Protocol) server for Steam Librarian
type Server struct {
	repo        *storage.Repository
	steamAPI    *steam.APIService
	syncService *services.LibrarySyncService
	logger      *logrus.Logger
}

// NewServer creates a new MCP server instance
func NewServer(repo *storage.Repository, steamAPI *steam.APIService, syncService *services.LibrarySyncService, logger *logrus.Logger) *Server {
	return &Server{
		repo:        repo,
		steamAPI:    steamAPI,
		syncService: syncService,
		logger:      logger,
	}
}

// MCPRequest represents an incoming MCP request
type MCPRequest struct {
	JSONRPC string                 `json:"jsonrpc"`
	Method  string                 `json:"method"`
	Params  map[string]interface{} `json:"params,omitempty"`
	ID      interface{}            `json:"id"`
}

// MCPResponse represents an outgoing MCP response
type MCPResponse struct {
	JSONRPC string      `json:"jsonrpc"`
	Result  interface{} `json:"result,omitempty"`
	Error   *MCPError   `json:"error,omitempty"`
	ID      interface{} `json:"id"`
}

// MCPError represents an MCP error response
type MCPError struct {
	Code    int         `json:"code"`
	Message string      `json:"message"`
	Data    interface{} `json:"data,omitempty"`
}

// Start starts the MCP server and begins processing requests
func (s *Server) Start(ctx context.Context) error {
	s.logger.Info("MCP server starting, listening on stdin/stdout")

	scanner := bufio.NewScanner(os.Stdin)
	writer := os.Stdout

	for {
		select {
		case <-ctx.Done():
			s.logger.Info("MCP server shutting down")
			return nil
		default:
			if scanner.Scan() {
				requestLine := scanner.Text()
				if requestLine == "" {
					continue
				}

				s.logger.WithField("request", requestLine).Debug("Received MCP request")

				response, err := s.handleRequest(requestLine)
				if err != nil {
					s.logger.WithError(err).Error("Failed to handle MCP request")
					continue
				}

				if _, err := writer.Write(append(response, '\n')); err != nil {
					s.logger.WithError(err).Error("Failed to write MCP response")
					continue
				}
			}

			if err := scanner.Err(); err != nil {
				if err == io.EOF {
					s.logger.Info("MCP server received EOF, shutting down")
					return nil
				}
				s.logger.WithError(err).Error("Scanner error")
				return err
			}
		}
	}
}

// handleRequest processes a single MCP request
func (s *Server) handleRequest(requestLine string) ([]byte, error) {
	var req MCPRequest
	if err := json.Unmarshal([]byte(requestLine), &req); err != nil {
		return s.createErrorResponse(nil, -32700, "Parse error", err.Error())
	}

	s.logger.WithFields(logrus.Fields{
		"method": req.Method,
		"id":     req.ID,
	}).Debug("Processing MCP request")

	var response MCPResponse
	response.JSONRPC = "2.0"
	response.ID = req.ID

	// Route requests based on method
	switch req.Method {
	case "initialize":
		response.Result = s.handleInitialize(req.Params)
	case "steam_librarian/list_libraries":
		result, err := s.handleListLibraries(req.Params)
		if err != nil {
			response.Error = &MCPError{Code: -32603, Message: "Internal error", Data: err.Error()}
		} else {
			response.Result = result
		}
	case "steam_librarian/list_games":
		result, err := s.handleListGames(req.Params)
		if err != nil {
			response.Error = &MCPError{Code: -32603, Message: "Internal error", Data: err.Error()}
		} else {
			response.Result = result
		}
	case "steam_librarian/get_library":
		result, err := s.handleGetLibrary(req.Params)
		if err != nil {
			response.Error = &MCPError{Code: -32603, Message: "Internal error", Data: err.Error()}
		} else {
			response.Result = result
		}
	case "steam_librarian/get_game":
		result, err := s.handleGetGame(req.Params)
		if err != nil {
			response.Error = &MCPError{Code: -32603, Message: "Internal error", Data: err.Error()}
		} else {
			response.Result = result
		}
	case "steam_librarian/sync_library":
		result, err := s.handleSyncLibrary(req.Params)
		if err != nil {
			response.Error = &MCPError{Code: -32603, Message: "Internal error", Data: err.Error()}
		} else {
			response.Result = result
		}
	case "steam_librarian/get_sync_progress":
		result, err := s.handleGetSyncProgress(req.Params)
		if err != nil {
			response.Error = &MCPError{Code: -32603, Message: "Internal error", Data: err.Error()}
		} else {
			response.Result = result
		}
	case "steam_librarian/get_sync_history":
		result, err := s.handleGetSyncHistory(req.Params)
		if err != nil {
			response.Error = &MCPError{Code: -32603, Message: "Internal error", Data: err.Error()}
		} else {
			response.Result = result
		}
	case "steam_librarian/cancel_sync":
		result, err := s.handleCancelSync(req.Params)
		if err != nil {
			response.Error = &MCPError{Code: -32603, Message: "Internal error", Data: err.Error()}
		} else {
			response.Result = result
		}
	case "steam_librarian/get_active_syncs":
		result, err := s.handleGetActiveSyncs(req.Params)
		if err != nil {
			response.Error = &MCPError{Code: -32603, Message: "Internal error", Data: err.Error()}
		} else {
			response.Result = result
		}
	case "steam_librarian/get_conflicts":
		result, err := s.handleGetConflicts(req.Params)
		if err != nil {
			response.Error = &MCPError{Code: -32603, Message: "Internal error", Data: err.Error()}
		} else {
			response.Result = result
		}
	case "steam_librarian/resolve_conflict":
		result, err := s.handleResolveConflict(req.Params)
		if err != nil {
			response.Error = &MCPError{Code: -32603, Message: "Internal error", Data: err.Error()}
		} else {
			response.Result = result
		}
	case "steam_librarian/auto_resolve_conflicts":
		result, err := s.handleAutoResolveConflicts(req.Params)
		if err != nil {
			response.Error = &MCPError{Code: -32603, Message: "Internal error", Data: err.Error()}
		} else {
			response.Result = result
		}
	case "steam_librarian/get_conflict_statistics":
		result, err := s.handleGetConflictStatistics(req.Params)
		if err != nil {
			response.Error = &MCPError{Code: -32603, Message: "Internal error", Data: err.Error()}
		} else {
			response.Result = result
		}
	case "steam_librarian/get_stats":
		result, err := s.handleGetStats(req.Params)
		if err != nil {
			response.Error = &MCPError{Code: -32603, Message: "Internal error", Data: err.Error()}
		} else {
			response.Result = result
		}
	default:
		response.Error = &MCPError{
			Code:    -32601,
			Message: "Method not found",
			Data:    req.Method,
		}
	}

	return json.Marshal(response)
}

// createErrorResponse creates a standardized error response
func (s *Server) createErrorResponse(id interface{}, code int, message, data string) ([]byte, error) {
	response := MCPResponse{
		JSONRPC: "2.0",
		ID:      id,
		Error: &MCPError{
			Code:    code,
			Message: message,
			Data:    data,
		},
	}
	return json.Marshal(response)
}

// Handler methods for different MCP operations

// handleInitialize handles the MCP initialization request
func (s *Server) handleInitialize(params map[string]interface{}) map[string]interface{} {
	return map[string]interface{}{
		"protocolVersion": "2024-11-05",
		"capabilities": map[string]interface{}{
			"tools": map[string]interface{}{
				"listChanged": false,
			},
			"resources": map[string]interface{}{
				"subscribe": false,
			},
		},
		"serverInfo": map[string]interface{}{
			"name":        "steam-librarian",
			"version":     "0.1.0",
			"description": "Steam library management with sync capabilities",
		},
		"supportedMethods": []string{
			"steam_librarian/list_libraries",
			"steam_librarian/list_games", 
			"steam_librarian/get_library",
			"steam_librarian/get_game",
			"steam_librarian/sync_library",
			"steam_librarian/get_sync_progress",
			"steam_librarian/get_sync_history",
			"steam_librarian/cancel_sync",
			"steam_librarian/get_active_syncs",
			"steam_librarian/get_conflicts",
			"steam_librarian/resolve_conflict",
			"steam_librarian/auto_resolve_conflicts",
			"steam_librarian/get_conflict_statistics",
			"steam_librarian/get_stats",
		},
	}
}

// handleListLibraries returns all libraries
func (s *Server) handleListLibraries(params map[string]interface{}) (map[string]interface{}, error) {
	libraries, err := s.repo.GetAllLibraries()
	if err != nil {
		return nil, fmt.Errorf("failed to get libraries: %w", err)
	}

	return map[string]interface{}{
		"libraries": libraries,
		"count":     len(libraries),
	}, nil
}

// handleListGames returns all games, optionally filtered by library
func (s *Server) handleListGames(params map[string]interface{}) (map[string]interface{}, error) {
	// Check if library_id parameter is provided
	if libraryIDStr, ok := params["library_id"].(string); ok {
		// Get games for specific library
		games, err := s.repo.GetGamesByUserID(libraryIDStr)
		if err != nil {
			return nil, fmt.Errorf("failed to get games for library: %w", err)
		}
		return map[string]interface{}{
			"games":      games,
			"count":      len(games),
			"library_id": libraryIDStr,
		}, nil
	}

	// Get all games
	games, err := s.repo.GetAllGames()
	if err != nil {
		return nil, fmt.Errorf("failed to get games: %w", err)
	}

	return map[string]interface{}{
		"games": games,
		"count": len(games),
	}, nil
}

// handleGetLibrary returns a specific library by ID
func (s *Server) handleGetLibrary(params map[string]interface{}) (map[string]interface{}, error) {
	idStr, ok := params["id"].(string)
	if !ok {
		return nil, fmt.Errorf("library ID is required")
	}

	id, err := strconv.ParseUint(idStr, 10, 32)
	if err != nil {
		return nil, fmt.Errorf("invalid library ID: %s", idStr)
	}

	library, err := s.repo.GetLibraryByID(uint(id))
	if err != nil {
		return nil, fmt.Errorf("failed to get library: %w", err)
	}

	if library == nil {
		return nil, fmt.Errorf("library not found")
	}

	return map[string]interface{}{
		"library": library,
	}, nil
}

// handleGetGame returns a specific game by ID
func (s *Server) handleGetGame(params map[string]interface{}) (map[string]interface{}, error) {
	idStr, ok := params["id"].(string)
	if !ok {
		return nil, fmt.Errorf("game ID is required")
	}

	id, err := strconv.ParseUint(idStr, 10, 32)
	if err != nil {
		return nil, fmt.Errorf("invalid game ID: %s", idStr)
	}

	game, err := s.repo.GetGameByID(uint(id))
	if err != nil {
		return nil, fmt.Errorf("failed to get game: %w", err)
	}

	if game == nil {
		return nil, fmt.Errorf("game not found")
	}

	return map[string]interface{}{
		"game": game,
	}, nil
}

// handleSyncLibrary triggers a library sync operation
func (s *Server) handleSyncLibrary(params map[string]interface{}) (map[string]interface{}, error) {
	steamUserID, ok := params["steam_user_id"].(string)
	if !ok {
		return nil, fmt.Errorf("steam_user_id is required")
	}

	// Get sync type (default to incremental)
	syncTypeStr, _ := params["sync_type"].(string)
	if syncTypeStr == "" {
		syncTypeStr = "incremental"
	}

	var syncType services.SyncType
	switch syncTypeStr {
	case "full":
		syncType = services.SyncTypeFull
	case "incremental":
		syncType = services.SyncTypeIncremental
	default:
		return nil, fmt.Errorf("invalid sync_type. Use 'full' or 'incremental'")
	}

	s.logger.WithFields(logrus.Fields{
		"steam_user_id": steamUserID,
		"sync_type":     syncTypeStr,
	}).Info("Starting library sync via MCP")

	// Start async sync
	progress, err := s.syncService.SyncLibraryAsync(steamUserID, syncType)
	if err != nil {
		return nil, fmt.Errorf("failed to start sync: %w", err)
	}

	return map[string]interface{}{
		"status":        "started",
		"steam_user_id": steamUserID,
		"sync_type":     syncTypeStr,
		"progress":      progress,
		"message":       "Library sync started successfully",
	}, nil
}

// handleGetStats returns statistics for libraries and games
func (s *Server) handleGetStats(params map[string]interface{}) (map[string]interface{}, error) {
	// Get library count
	libraries, err := s.repo.GetAllLibraries()
	if err != nil {
		return nil, fmt.Errorf("failed to get libraries: %w", err)
	}

	// Get game count
	games, err := s.repo.GetAllGames()
	if err != nil {
		return nil, fmt.Errorf("failed to get games: %w", err)
	}

	// Calculate basic statistics
	totalPlaytime := 0
	neverPlayed := 0
	for _, game := range games {
		totalPlaytime += game.PlaytimeForever
		if game.PlaytimeForever == 0 {
			neverPlayed++
		}
	}

	return map[string]interface{}{
		"total_libraries": len(libraries),
		"total_games":     len(games),
		"total_playtime":  totalPlaytime,
		"never_played":    neverPlayed,
		"stats_generated": "2024-01-01T00:00:00Z", // TODO: Use actual timestamp
	}, nil
}

// handleGetSyncProgress returns the current sync progress for a user
func (s *Server) handleGetSyncProgress(params map[string]interface{}) (map[string]interface{}, error) {
	steamUserID, ok := params["steam_user_id"].(string)
	if !ok {
		return nil, fmt.Errorf("steam_user_id is required")
	}

	progress, exists := s.syncService.GetSyncProgress(steamUserID)
	if !exists {
		return map[string]interface{}{
			"steam_user_id": steamUserID,
			"active":        false,
			"message":       "No active sync found for this user",
		}, nil
	}

	return map[string]interface{}{
		"steam_user_id": steamUserID,
		"active":        true,
		"progress":      progress,
	}, nil
}

// handleGetSyncHistory returns the sync history for a user
func (s *Server) handleGetSyncHistory(params map[string]interface{}) (map[string]interface{}, error) {
	steamUserID, ok := params["steam_user_id"].(string)
	if !ok {
		return nil, fmt.Errorf("steam_user_id is required")
	}

	history := s.syncService.GetSyncHistory(steamUserID)

	return map[string]interface{}{
		"steam_user_id": steamUserID,
		"history":       history,
		"count":         len(history),
	}, nil
}

// handleCancelSync cancels an active sync operation
func (s *Server) handleCancelSync(params map[string]interface{}) (map[string]interface{}, error) {
	steamUserID, ok := params["steam_user_id"].(string)
	if !ok {
		return nil, fmt.Errorf("steam_user_id is required")
	}

	err := s.syncService.CancelSync(steamUserID)
	if err != nil {
		return nil, fmt.Errorf("failed to cancel sync: %w", err)
	}

	return map[string]interface{}{
		"steam_user_id": steamUserID,
		"status":        "cancelled",
		"message":       "Sync cancelled successfully",
	}, nil
}

// handleGetActiveSyncs returns all currently active sync operations
func (s *Server) handleGetActiveSyncs(params map[string]interface{}) (map[string]interface{}, error) {
	activeSyncs := s.syncService.GetActiveSyncs()

	return map[string]interface{}{
		"active_syncs": activeSyncs,
		"count":        len(activeSyncs),
	}, nil
}

// handleGetConflicts returns conflicts based on optional filters
func (s *Server) handleGetConflicts(params map[string]interface{}) (map[string]interface{}, error) {
	conflictResolver := s.syncService.GetConflictResolver()
	
	statusParam, _ := params["status"].(string)
	typeParam, _ := params["type"].(string)
	
	var status services.ConflictStatus
	var conflictType services.ConflictType
	
	if statusParam != "" {
		status = services.ConflictStatus(statusParam)
	}
	if typeParam != "" {
		conflictType = services.ConflictType(typeParam)
	}
	
	conflicts := conflictResolver.GetConflicts(status, conflictType)
	
	return map[string]interface{}{
		"conflicts": conflicts,
		"count":     len(conflicts),
		"filters": map[string]interface{}{
			"status": statusParam,
			"type":   typeParam,
		},
	}, nil
}

// handleResolveConflict resolves a specific conflict
func (s *Server) handleResolveConflict(params map[string]interface{}) (map[string]interface{}, error) {
	conflictID, ok := params["conflict_id"].(string)
	if !ok {
		return nil, fmt.Errorf("conflict_id is required")
	}
	
	strategyStr, ok := params["strategy"].(string)
	if !ok {
		return nil, fmt.Errorf("strategy is required")
	}
	
	resolvedBy, _ := params["resolved_by"].(string)
	if resolvedBy == "" {
		resolvedBy = "mcp-user"
	}
	
	strategy := services.ConflictResolutionStrategy(strategyStr)
	conflictResolver := s.syncService.GetConflictResolver()
	
	if err := conflictResolver.ResolveConflict(conflictID, strategy, resolvedBy); err != nil {
		return nil, fmt.Errorf("failed to resolve conflict: %w", err)
	}
	
	return map[string]interface{}{
		"message":     "Conflict resolved successfully",
		"conflict_id": conflictID,
		"strategy":    strategy,
		"resolved_by": resolvedBy,
	}, nil
}

// handleAutoResolveConflicts triggers automatic conflict resolution
func (s *Server) handleAutoResolveConflicts(params map[string]interface{}) (map[string]interface{}, error) {
	conflictResolver := s.syncService.GetConflictResolver()
	
	if err := conflictResolver.AutoResolveConflicts(); err != nil {
		return nil, fmt.Errorf("auto-resolution failed: %w", err)
	}
	
	return map[string]interface{}{
		"message": "Auto-resolution completed successfully",
	}, nil
}

// handleGetConflictStatistics returns conflict resolution statistics
func (s *Server) handleGetConflictStatistics(params map[string]interface{}) (map[string]interface{}, error) {
	conflictResolver := s.syncService.GetConflictResolver()
	stats := conflictResolver.GetStatistics()
	
	return map[string]interface{}{
		"statistics": stats,
	}, nil
}